import pandas as pd

from app.config import get_settings
from app.services.llm_sentiment import estimate_cost
from app.tasks.daily_scan import _ohlcv_summary, celery_app


class TestEstimateCost:
    def test_haiku_input_rate(self):
        assert estimate_cost("claude-haiku-4-5", 1_000_000, 0) == 1.0

    def test_haiku_output_rate(self):
        assert estimate_cost("claude-haiku-4-5", 0, 1_000_000) == 5.0

    def test_output_tokens_priced_higher_than_input(self):
        model = "claude-sonnet-5"
        assert estimate_cost(model, 0, 1_000_000) > estimate_cost(model, 1_000_000, 0)

    def test_tiers_are_ordered(self):
        haiku = estimate_cost("claude-haiku-4-5", 10_000, 1_000)
        sonnet = estimate_cost("claude-sonnet-5", 10_000, 1_000)
        opus = estimate_cost("claude-opus-5", 10_000, 1_000)
        assert haiku < sonnet < opus

    def test_unknown_model_falls_back_to_sonnet_rate(self):
        assert estimate_cost("some-future-model", 10_000, 1_000) == estimate_cost(
            "claude-sonnet-5", 10_000, 1_000
        )


class TestConfiguredModels:
    def test_model_ids_carry_no_date_suffix(self):
        settings = get_settings()
        for model in (settings.sentiment_model_batch, settings.sentiment_model_deep):
            assert not model[-1].isdigit() or "-20" not in model

    def test_configured_models_are_priced(self):
        settings = get_settings()
        for model in (settings.sentiment_model_batch, settings.sentiment_model_deep):
            assert estimate_cost(model, 1_000_000, 0) > 0

    def test_batch_model_cheaper_than_deep_model(self):
        settings = get_settings()
        assert estimate_cost(settings.sentiment_model_batch, 10_000, 1_000) < estimate_cost(
            settings.sentiment_model_deep, 10_000, 1_000
        )


class TestOhlcvSummary:
    def test_reports_current_price(self):
        df = pd.DataFrame({"close": [100.0, 105.0]})
        assert _ohlcv_summary(df)["current_price"] == 105.0

    def test_short_series_omits_change_fields(self):
        summary = _ohlcv_summary(pd.DataFrame({"close": [50.0, 51.0]}))
        assert "change_1w_pct" not in summary
        assert "change_1m_pct" not in summary

    def test_computes_percentage_changes(self):
        df = pd.DataFrame({"close": [100.0] * 30 + [110.0]})
        summary = _ohlcv_summary(df)
        assert summary["change_1w_pct"] == 10.0
        assert summary["change_1m_pct"] == 10.0

    def test_handles_zero_prior_price(self):
        df = pd.DataFrame({"close": [0.0] * 30 + [10.0]})
        summary = _ohlcv_summary(df)
        assert summary["current_price"] == 10.0
        assert "change_1m_pct" not in summary


class TestBeatSchedule:
    def test_sentiment_batch_runs_before_daily_scan(self):
        schedule = celery_app.conf.beat_schedule
        sentiment_hour = schedule["sentiment-batch"]["schedule"].hour
        scan_hour = schedule["daily-scan"]["schedule"].hour
        assert min(sentiment_hour) < min(scan_hour)
