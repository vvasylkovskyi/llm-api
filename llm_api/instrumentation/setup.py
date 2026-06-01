import logging
import os

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from phoenix.otel import register

from llm_api.settings.app import AppSettings

logger = logging.getLogger(__name__)


class InstrumentationSetup:
    @staticmethod
    def setup_arize_traces(settings: AppSettings) -> None:
        register(
            project_name="default",
            auto_instrument=True,
            endpoint=settings.phoenix_collector_endpoint,
        )
        logger.info("Arize traces initialized")

    @staticmethod
    def setup_otel(settings: AppSettings) -> None:
        resource = Resource(attributes={"service.name": os.getenv("SERVICE_NAME", "default-service")})
        exporter = OTLPMetricExporter(endpoint=f"http://{settings.alloy_host}:4318/v1/metrics")
        reader = PeriodicExportingMetricReader(exporter, export_interval_millis=15_000)
        provider = MeterProvider(resource=resource, metric_readers=[reader])
        metrics.set_meter_provider(provider)
        logger.info("OTel metrics initialized")
