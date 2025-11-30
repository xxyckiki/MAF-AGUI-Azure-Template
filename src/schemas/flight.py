from pydantic import BaseModel, Field


class FlightPriceInfo(BaseModel):
    """Flight ticket price information between two locations."""

    departure: str = Field(description="The departure city or airport code")
    destination: str = Field(description="The destination city or airport code")
    price: float = Field(description="The ticket price in USD")
    currency: str = Field(default="USD", description="The currency of the price")
    airline: str | None = Field(default=None, description="The airline company")
    flight_class: str | None = Field(
        default=None, description="Economy, Business, or First class"
    )
