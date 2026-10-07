"""Расчёт по переданным цепочкам: без сети и скрытых расписаний."""

from datetime import timedelta

from trip_planner.models import Chain, PlanRequest, PlanResult, Trip


def _minutes(delta):
    return delta.total_seconds() / 60


def _event(kind, start, end, description, **extra):
    return {
        "kind": kind,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "minutes": _minutes(end - start),
        "description": description,
        **extra,
    }


def _option(chain: Chain, trips: list[Trip], boarding: int):
    leave = trips[0].departure - timedelta(
        minutes=chain.access.minutes + boarding
    )
    access_end = trips[0].departure - timedelta(minutes=boarding)
    arrive = trips[-1].arrival + timedelta(minutes=chain.egress.minutes)
    timeline = [
        _event(
            "access",
            leave,
            access_end,
            chain.access.description,
            basis=chain.access.basis,
            estimated=True,
        ),
        _event("wait", access_end, trips[0].departure, "Запас на посадку"),
    ]
    waiting = boarding
    for index, trip in enumerate(trips):
        stage = chain.stages[index]
        if index:
            transfer = chain.transfers[index - 1]
            previous = trips[index - 1].arrival
            walked = previous + timedelta(minutes=transfer.walk_minutes)
            timeline += [
                _event(
                    "walk",
                    previous,
                    walked,
                    "Переход между остановками",
                    from_stop=transfer.from_stop,
                    to_stop=transfer.to_stop,
                    estimated=True,
                ),
                _event(
                    "wait",
                    walked,
                    trip.departure,
                    "Ожидание с запасом на пересадку",
                    buffer_minutes=transfer.buffer_minutes,
                ),
            ]
            waiting += _minutes(trip.departure - walked)
        timeline.append(
            _event(
                "ride",
                trip.departure,
                trip.arrival,
                trip.label,
                trip_id=trip.id,
                mode=trip.mode,
                from_stop=stage.from_stop,
                to_stop=stage.to_stop,
                from_name=stage.from_name,
                to_name=stage.to_name,
                source_id=trip.source_id,
            )
        )
    timeline.append(
        _event(
            "egress",
            trips[-1].arrival,
            arrive,
            chain.egress.description,
            basis=chain.egress.basis,
            estimated=True,
        )
    )
    return {
        "chain_id": chain.id,
        "origin": chain.origin,
        "destination": chain.destination,
        "leave_at": leave.isoformat(),
        "arrive_at": arrive.isoformat(),
        "total_minutes": _minutes(arrive - leave),
        "waiting_minutes": waiting,
        "transfer_count": len(trips) - 1,
        "timeline": timeline,
    }


def _connections(chain, available, boarding, window):
    """Отсечь недостижимые рейсы до раскрытия следующего этапа."""

    def visit(chosen):
        index = len(chosen)
        if index == len(available):
            yield _option(chain, chosen, boarding)
            return
        for trip in available[index]:
            if chosen:
                transfer = chain.transfers[index - 1]
                earliest = chosen[-1].arrival + timedelta(
                    minutes=transfer.walk_minutes + transfer.buffer_minutes
                )
                if trip.departure < earliest:
                    continue
            else:
                leave = trip.departure - timedelta(
                    minutes=chain.access.minutes + boarding
                )
                if not window.start <= leave <= window.end:
                    continue
            yield from visit([*chosen, trip])

    yield from visit([])


def _identity(option):
    return (
        option["origin"],
        option["destination"],
        tuple(
            (
                event["kind"],
                event["start"],
                event["end"],
                event.get("from_stop"),
                event.get("to_stop"),
                event.get("trip_id"),
            )
            for event in option["timeline"]
        ),
    )


def _rank(option):
    return (
        option["total_minutes"],
        option["waiting_minutes"],
        option["transfer_count"],
        option["leave_at"],
        option["chain_id"],
        _identity(option),
    )


def plan_departures(request: PlanRequest) -> PlanResult:
    """Выбрать до пяти вариантов среди подтверждённых входных данных."""
    sources = {source.id: source for source in request.sources}
    warnings = []
    incomplete = False
    best = {}
    for chain in request.chains:
        if chain.coverage != "complete":
            incomplete = True
            warnings.append(f"{chain.id}: покрытие {chain.coverage}")
        available = []
        for stage in chain.stages:
            verified = []
            for trip in stage.trips:
                source = sources[trip.source_id]
                if (
                    source.verified
                    and trip.departure.date() in source.valid_dates
                ):
                    verified.append(trip)
                else:
                    incomplete = True
                    warnings.append(
                        f"{chain.id}/{trip.id}: источник не подтверждён "
                        "или не применим к дате рейса"
                    )
            available.append(verified)
        for option in _connections(
            chain,
            available,
            request.boarding_buffer_minutes,
            request.departure_window,
        ):
            key = _identity(option)
            if key not in best or _rank(option) < _rank(best[key]):
                best[key] = option
            if len(best) > request.max_options:
                del best[max(best, key=lambda key: _rank(best[key]))]
    options = sorted(best.values(), key=_rank)
    modes = {source.mode == "fixture" for source in request.sources}
    data_kind = (
        "mixed" if len(modes) > 1 else ("fixture" if True in modes else "real")
    )
    if data_kind != "real":
        warnings.append("Есть вымышленные данные: это не реальная поездка.")
    warnings.append(
        "Городские и пешие участки оценочные. "
        "Перед поездкой проверьте изменения расписаний."
    )
    return {
        "status": "ok"
        if options
        else ("needs_data" if incomplete else "no_routes"),
        "options": options,
        "warnings": list(dict.fromkeys(warnings)),
        "sources": [
            source.model_dump(mode="json") for source in request.sources
        ],
        "data_kind": data_kind,
        "search_scope": {
            "chains": [chain.id for chain in request.chains],
            "departure_window": request.departure_window.model_dump(
                mode="json"
            ),
            "max_scheduled_stages": 3,
            "complete": not incomplete,
            "claim": "Лучшие среди переданных проверенных цепочек",
        },
    }
