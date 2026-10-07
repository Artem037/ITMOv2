"""Проверка структуры запроса; данные не исправляются догадками."""

from datetime import date
from typing import Annotated, Any, Literal, TypedDict
from zoneinfo import ZoneInfo

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StrictBool,
    StrictInt,
    ValidationError,
    model_validator,
)

MOSCOW = ZoneInfo("Europe/Moscow")
Minutes = Annotated[StrictInt, Field(ge=0, le=1440)]
Text = Annotated[str, Field(min_length=1, max_length=500)]
Moment = Annotated[
    AwareDatetime, AfterValidator(lambda v: v.astimezone(MOSCOW))
]


class InputError(ValueError):
    """Невалидный вход с именем поля и причиной."""


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Window(Model):
    start: Moment
    end: Moment

    @model_validator(mode="after")
    def ordered(self):
        if self.end < self.start:
            raise ValueError("end должен быть не раньше start")
        return self


class Source(Model):
    id: Text
    url: HttpUrl
    checked_at: Moment
    valid_dates: list[date] = Field(min_length=1, max_length=31)
    mode: Literal["live", "manual", "fixture"]
    verified: StrictBool = False


class Access(Model):
    minutes: Minutes | None
    description: Text
    basis: Text
    source_ids: list[str] = Field(default_factory=list)


class Trip(Model):
    id: Text
    mode: Literal["bus", "suburban", "train", "metro", "tram"]
    label: Text
    departure: Moment
    arrival: Moment
    source_id: Text

    @model_validator(mode="after")
    def chronological(self):
        if self.arrival <= self.departure:
            raise ValueError("arrival должен быть позже departure")
        return self


class Stage(Model):
    from_stop: Text
    to_stop: Text
    from_name: Text
    to_name: Text
    trips: list[Trip] = Field(max_length=500)


class Transfer(Model):
    from_stop: Text
    to_stop: Text
    walk_minutes: Minutes
    buffer_minutes: Minutes


class Chain(Model):
    id: Text
    origin: Text
    destination: Text
    coverage: Literal["complete", "partial", "missing"]
    access: Access
    egress: Access
    stages: list[Stage] = Field(min_length=1, max_length=3)
    transfers: list[Transfer]

    @model_validator(mode="after")
    def connected(self):
        if len(self.transfers) != len(self.stages) - 1:
            raise ValueError("нужен один transfers между каждыми stages")
        for index, transfer in enumerate(self.transfers):
            if (
                transfer.from_stop != self.stages[index].to_stop
                or transfer.to_stop != self.stages[index + 1].from_stop
            ):
                raise ValueError("transfers не соединяет ID остановок stages")
        return self


class PlanRequest(Model):
    departure_window: Window
    timezone: Literal["Europe/Moscow"] = "Europe/Moscow"
    max_options: Annotated[StrictInt, Field(ge=1, le=5)] = 5
    boarding_buffer_minutes: Minutes = 10
    sources: list[Source] = Field(max_length=100)
    chains: list[Chain] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def references(self):
        sources = {source.id: source for source in self.sources}
        if len(sources) != len(self.sources):
            raise ValueError("sources.id должны быть уникальны")
        if len({chain.id for chain in self.chains}) != len(self.chains):
            raise ValueError("chains.id должны быть уникальны")
        for chain in self.chains:
            ids = chain.access.source_ids + chain.egress.source_ids
            ids += [
                trip.source_id
                for stage in chain.stages
                for trip in stage.trips
            ]
            unknown = set(ids) - sources.keys()
            if unknown:
                raise ValueError(f"source_id не найден: {sorted(unknown)}")
        return self


class PlanResult(TypedDict):
    status: Literal["ok", "no_routes", "needs_data"]
    options: list[dict[str, Any]]
    warnings: list[str]
    sources: list[dict[str, Any]]
    data_kind: Literal["fixture", "real", "mixed"]
    search_scope: dict[str, Any]


def parse_request(payload: dict) -> PlanRequest:
    """Проверить JSON, сохранив в диагностике путь ошибочного поля."""
    try:
        return PlanRequest.model_validate(payload)
    except ValidationError as error:
        details = "; ".join(
            f"{'.'.join(map(str, item['loc'])) or 'request'}: {item['msg']}"
            for item in error.errors(include_input=False, include_url=False)
        )
        raise InputError(details) from None
