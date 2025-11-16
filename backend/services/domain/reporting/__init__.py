#!/usr/bin/env python3
"""
Reporting orchestration: glues data preparation, computations, and HTML/chart helpers.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from backend.services.core.base import ServiceContext
from backend.services.data.db_manager import DbQueries
from backend.services.core.config import DEFAULT_CLIENT, verify_source_type
from backend.services.core.utils import ReportLogger
from backend.services.domain.data_preparation import DataPreparationOrchestrator
from backend.services.domain.electricity_analysis import ElectricityAnalysisOrchestrator
from backend.services.services.email import send_report_email
from backend.services.domain.reporting.prepare_charts import generate_charts
from backend.services.domain.reporting.prepare_html import generate_onepager_html
import re
import tempfile


class ReportingOrchestrator(ServiceContext):
    """
    End-to-end reporting workflow using the refactored services.
    """

    def __init__(
        self,
        *,
        user_id: Optional[int] = None,
        client_id: Optional[int] = None,
        tenant_id: Optional[int] = None,
        logger: Optional[ReportLogger] = None,
        conn: Optional[sqlite3.Connection] = None,
    ) -> None:
        super().__init__(
            user_id=user_id,
            client_id=client_id,
            tenant_id=tenant_id,
            logger=logger,
            conn=conn,
        )
        self.data_prep = DataPreparationOrchestrator(
            user_id=self.user_id,
            client_id=self.client_id,
            tenant_id=self.tenant_id,
            logger=self.logger,
            conn=self.conn,
        )
        self.analysis = ElectricityAnalysisOrchestrator(
            user_id=self.user_id,
            client_id=self.client_id,
            tenant_id=self.tenant_id,
            logger=self.logger,
            conn=self.conn,
            cutoff_manager=self.data_prep.cutoff_manager,
        )

    def generate_onepager_report(
        self,
        tenant_id: int,
        source: str = "meter_records",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Generate the complete data/metrics/chart/html bundle for a tenant.
        """
        df = self.data_prep.load_and_prepare_data_for_tenant(
            tenant_id=tenant_id,
            source=source,
            start_date=start_date,
            end_date=end_date,
        )
        tenant_info = self.db.get_tenant_info(tenant_id)
        self.logger.debug(f"Tenant info: {tenant_info}")
        label = tenant_info['name']

        analysis = self.analysis.computations_for_one_pager(
            df=df,
            tenant_id=tenant_id,
            label=label,
        )

        charts = generate_charts(
            df_daily=analysis['df_daily'],
            df_monthly=analysis['df_monthly'],
            df_avg_hourly_consumption=analysis['df_avg_hourly_consumption'],
            df_avg_daily_consumption=analysis['df_avg_daily_consumption'],
            last_month=analysis['last_month'],
            logger=self.logger,
        )

        html_values = {
            **analysis['kpis'],
            **analysis['power_metrics'],
            **analysis['time_consumption'],
            "date_range": analysis['date_range'],
        }
        html_content = generate_onepager_html(
            tenant_name=analysis['label'],
            values_for_html=html_values,
            charts=charts,
            logger=self.logger,
        )

        return {
            "analysis": analysis,
            "charts": charts,
            "html": html_content,
        }


__all__ = [
    "ReportingOrchestrator",
    "generate_report_for_tenant",
    "generate_reports_for_tenant",
    "generate_reports_for_client",
    "generate_report_for_tenant_artifacts",
    "execute_last_records_job",
    "execute_billing_info_job",
]


REPORTING_DIR = Path(__file__).resolve().parent
BACKEND_DIR = REPORTING_DIR.parent.parent
DEFAULT_REPORTS_DIR = BACKEND_DIR / "reports"


def generate_report_for_tenant_artifacts(
    tenant_id: int,
    client_id: Optional[int] = None,
    *,
    output_dir: Optional[Path] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    source: str = "meter_records",
    logger: Optional[ReportLogger] = None,
) -> tuple[Path, Dict[str, Any], str]:
    """
    Generate report artifacts for a tenant.

    Returns:
        A tuple of (report_path, metadata dict, html content).
    """
    logger = logger or ReportLogger()
    verify_source_type(source)

    resolved_client_id = client_id or DbQueries.get_client_id_for_tenant(tenant_id)

    orchestrator = ReportingOrchestrator(
        tenant_id=tenant_id,
        client_id=resolved_client_id,
        logger=logger,
    )
    bundle = orchestrator.generate_onepager_report(
        tenant_id=tenant_id,
        source=source,
        start_date=start_date,
        end_date=end_date,
    )

    html_content = bundle["html"]
    analysis = bundle["analysis"]
    tenant_name = analysis.get("label") or f"tenant_{tenant_id}"
    last_month = bundle["analysis"].get("last_month")
    date_range = bundle["analysis"].get("date_range")

    sanitized_tenant = re.sub(r"[^a-zA-Z0-9]", "_", tenant_name)
    sanitized_tenant = re.sub(r"_+", "_", sanitized_tenant).strip("_")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = output_dir or DEFAULT_REPORTS_DIR
    filepath = (
        output_dir
        / f"client_{resolved_client_id}/tenant_{sanitized_tenant}_{last_month}_{timestamp}.html"
    )
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(html_content, encoding="utf-8")

    client_name: Optional[str] = None
    if resolved_client_id is not None:
        client_row = DbQueries.get_client_by_id(resolved_client_id)
        if client_row:
            client_name = client_row["name"]

    metadata: Dict[str, Any] = {
        "client_id": resolved_client_id,
        "client_name": client_name,
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
        "last_month": last_month,
        "date_range": date_range,
    }

    logger.info(f"✅ Report written to {filepath}")
    return filepath, metadata, html_content


def generate_report_for_tenant(
    tenant_id: int,
    output_dir: Optional[Path] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    source: str = "meter_records",
    logger: Optional[ReportLogger] = None,
) -> Path:
    report_path, _, _ = generate_report_for_tenant_artifacts(
        tenant_id=tenant_id,
        client_id=None,
        output_dir=output_dir,
        start_date=start_date,
        end_date=end_date,
        source=source,
        logger=logger,
    )
    return report_path


def generate_reports_for_tenant(
    tenant_token: str,
    *,
    client_token: str = DEFAULT_CLIENT,
    logger: Optional[ReportLogger] = None,
    **_: object,
) -> None:
    """
    Trigger report generation for a tenant token.

    Placeholder implementation: logs intent; extend with real token→ID mapping later.
    """
    logger = logger or ReportLogger()
    logger.info(
        f"Report generation requested for tenant token '{tenant_token}' under client '{client_token}'."
    )


def generate_reports_for_client(
    client_token: str = DEFAULT_CLIENT,
    *,
    logger: Optional[ReportLogger] = None,
    **_: object,
) -> None:
    """Trigger report generation for all tenant tokens of a client (placeholder)."""
    logger = logger or ReportLogger()
    logger.info(f"Report generation requested for client token '{client_token}'.")


def execute_last_records_job(
    *,
    client_id: int,
    client_name: str,
    user_email: str,
) -> None:
    """Background task that generates last records CSV and emails it."""
    logger = ReportLogger()
    try:
        # Get data from query with n=1
        logger.info(f"Fetching last records for client {client_name} ({client_id})")
        df = DbQueries.get_last_n_records_for_client(client_id=client_id, n=1)
        
        if df.empty:
            logger.warning(f"No records found for client {client_name}")
            return
        
        # Set column names
        df.columns = [
            'building_name',
            'tenant_name',
            'unit_number',
            'meter_ref',
            'description',
            'timestamp_record',
            'meter_kW'
        ]
        
        # Create CSV file in temp directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"last_records_{client_name.replace(' ', '_')}_{timestamp}.csv"
        csv_path = Path(tempfile.gettempdir()) / filename
        df.to_csv(csv_path, index=False)
        
        logger.info(f"✅ CSV generated at {csv_path}")
        
        # Send email with CSV attachment
        success = send_report_email(
            email=user_email,
            client_name=client_name,
            tenant_name="All Tenants",
            last_month=None,
            attachments=[csv_path],
            logger=logger,
        )
        
        if success:
            logger.info(f"📬 Last records email sent to {user_email}")
        else:
            logger.warning(f"⚠️ Failed to send last records email to {user_email}")
            
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error(f"❌ Error generating last records for client {client_id}: {exc}")


def execute_billing_info_job(
    *,
    client_id: int,
    client_name: str,
    user_email: str,
) -> None:
    """Background task that generates billing info CSV with pandas processing and emails it."""
    logger = ReportLogger()
    try:
        # Get data from query with n=2
        logger.info(f"Fetching billing info for client {client_name} ({client_id})")
        df = DbQueries.get_last_n_records_for_client(client_id=client_id, n=2)
        
        if df.empty:
            logger.warning(f"No records found for client {client_name}")
            return
        
        # Set column names
        df.columns = [
            'building_name',
            'tenant_name',
            'unit_number',
            'meter_ref',
            'description',
            'timestamp_record',
            'meter_kW'
        ]
        
        # Convert timestamp_record to datetime
        df['timestamp_record'] = pd.to_datetime(df['timestamp_record'])
        
        # Sort by building, tenant, unit, and timestamp
        df = df.sort_values(['building_name', 'tenant_name', 'unit_number', 'timestamp_record'], 
                           ascending=[True, True, True, False])
        
        # Group by building, tenant, unit and calculate differences
        df_grouped = df.groupby(['building_name', 'tenant_name', 'unit_number', 'meter_ref'])
        
        # Create a new dataframe with the most recent record and previous record
        billing_records = []
        for group_key, group in df_grouped:
            # group_key is a tuple when grouping by multiple columns
            if isinstance(group_key, tuple) and len(group_key) == 4:
                building, tenant, unit, meter_ref = group_key
            else:
                logger.warning(f"Unexpected group_key format: {group_key}")
                continue
            if len(group) >= 2:
                # Get the two most recent records
                recent = group.iloc[0]
                previous = group.iloc[1]
                
                # Calculate consumption difference
                consumption_kWh = recent['meter_kW'] - previous['meter_kW']
                days_diff = (recent['timestamp_record'] - previous['timestamp_record']).days
                
                billing_records.append({
                    'building_name': building,
                    'tenant_name': tenant,
                    'unit_number': unit,
                    'meter_ref': meter_ref,
                    'description': recent['description'],
                    'current_reading': recent['meter_kW'],
                    'current_date': recent['timestamp_record'].strftime('%Y-%m-%d %H:%M:%S'),
                    'previous_reading': previous['meter_kW'],
                    'previous_date': previous['timestamp_record'].strftime('%Y-%m-%d %H:%M:%S'),
                    'consumption_kWh': consumption_kWh,
                    'days_between_readings': days_diff,
                })
            elif len(group) == 1:
                # Only one reading available
                recent = group.iloc[0]
                billing_records.append({
                    'building_name': building,
                    'tenant_name': tenant,
                    'unit_number': unit,
                    'meter_ref': meter_ref,
                    'description': recent['description'],
                    'current_reading': recent['meter_kW'],
                    'current_date': recent['timestamp_record'].strftime('%Y-%m-%d %H:%M:%S'),
                    'previous_reading': None,
                    'previous_date': None,
                    'consumption_kWh': None,
                    'days_between_readings': None,
                })
        
        # Create DataFrame from billing records
        billing_df = pd.DataFrame(billing_records)
        
        # Create CSV file in temp directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"billing_info_{client_name.replace(' ', '_')}_{timestamp}.csv"
        csv_path = Path(tempfile.gettempdir()) / filename
        billing_df.to_csv(csv_path, index=False)
        
        logger.info(f"✅ Billing info CSV generated at {csv_path}")
        
        # Send email with CSV attachment
        success = send_report_email(
            email=user_email,
            client_name=client_name,
            tenant_name="All Tenants",
            last_month=None,
            attachments=[csv_path],
            logger=logger,
        )
        
        if success:
            logger.info(f"📬 Billing info email sent to {user_email}")
        else:
            logger.warning(f"⚠️ Failed to send billing info email to {user_email}")
            
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error(f"❌ Error generating billing info for client {client_id}: {exc}")

