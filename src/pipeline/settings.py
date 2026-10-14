import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()



class Settings(BaseModel):
    #questions_csv: Path = Path("data/questions_small.csv") //for sanity test //later removed this file
    questions_csv: Path = Path("data/questions.csv")
    results_json: Path = Path("results.json")
    results_db: Path = Path("results.db")

    batch_size: int = Field(5, gt=0, le=20)
    #fail_rate: float = Field(0.3, ge=0.0, le=1.0)
    #fail_rate: float = Field(0.2, ge=0.0, le=1.0) #Rather than keep rerunning at 0.3, the guide suggests dropping the rate to 0.2 if this happens.

    #after verifying retry behavior, restore the default fail_rate
    fail_rate: float = Field(0.0, ge=0.0, le=1.0)

    openai_api_key: str = Field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", "")
    )

    max_retries: int = Field(2, ge=0)
    retry_delay_s: float = Field(1.0, ge=0.0)

    model: str = "gpt-4o-mini"
    #use_fake: bool = True
    use_fake: bool = False


class RunSummary(BaseModel):
    started_at: float
    elapsed_seconds: float = Field(ge=0.0)
    n_questions: int = Field(ge=0)
    n_succeeded: int = Field(ge=0)
    n_retries_total: int = Field(ge=0)
    total_cost_usd: float = Field(ge=0.0)
    fail_rate: float = Field(ge=0.0, le=1.0)
    use_fake: bool