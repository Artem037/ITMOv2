"""Локальный MCP-сервер: один инструмент расчёта без сетевых запросов."""

from mcp.server import MCPServer

from trip_planner.models import PlanRequest, PlanResult
from trip_planner.planner import plan_departures as calculate

mcp = MCPServer("transit-trip-planner", log_level="ERROR")


@mcp.tool(structured_output=True)
def plan_departures(request: PlanRequest) -> PlanResult:
    """Выбрать до 5 выходов по проверенным расписаниям с запасом пересадок.

    Источники собирает вызывающий агент. Fixture не является реальной
    поездкой; неизвестные данные возвращаются как needs_data.
    """
    return calculate(request)


if __name__ == "__main__":
    mcp.run(transport="stdio")
