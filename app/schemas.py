from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    features: list[float] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="List of 4 numerical features.",
    )


class PredictionResponse(BaseModel):
    prediction: int
    drift_detected: bool
