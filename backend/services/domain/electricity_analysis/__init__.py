#!/usr/bin/env python3
"""
Electricity Analysis Module

This module provides classes and functions for analyzing electricity consumption data.
"""

# Import classes
from backend.services.domain.electricity_analysis.computations import Computations

from datetime import datetime
from typing import Optional, Dict, Any
import pandas as pd
import sqlite3
from backend.services.core.utils import ReportLogger
from backend.services.domain.data_preparation import CutoffManager, DataFramePreparer
from backend.services.core.base import ServiceContext



# ============================================================================
# Context-aware Orchestrator Class
# ============================================================================

class ElectricityAnalysisOrchestrator(ServiceContext):
    """
    Orchestrates electricity analysis computations with shared context.
    
    Holds user_id, client_id, and manages shared resources.
    Instantiate once per request/session from frontend context.
    
    Usage:
        # In your API endpoint/request handler:
        orchestrator = ElectricityAnalysisOrchestrator(
            user_id=request.user_id,      # From frontend context
            client_id=request.client_id,  # From frontend context
            logger=logger,
            conn=db_conn                  # Optional: share connection
        )
        
        # Run computations for one-pager:
        results = orchestrator.computations_for_one_pager(
            df=prepared_df,
            tenant_id=tenant_id,
            label=label,
        )
    """
    
    def __init__(
        self,
        user_id: Optional[int] = None,
        client_id: Optional[int] = None,
        tenant_id: Optional[int] = None,
        logger: Optional[ReportLogger] = None,
        conn: Optional[sqlite3.Connection] = None,
        cutoff_manager: Optional[CutoffManager] = None,
    ):
        """
        Initialize orchestrator with user context.
        
        Args:
            user_id: User ID from frontend context
            client_id: Client ID from frontend context
            logger: Logger instance
            conn: Optional database connection (shared across operations)
            cutoff_manager: Optional shared CutoffManager instance from data preparation
        """
        super().__init__(
            user_id=user_id,
            client_id=client_id,
            tenant_id=tenant_id,
            logger=logger,
            conn=conn,
        )

        # Initialize component classes with shared context
        self.computations = Computations(
            user_id=self.user_id,
            client_id=self.client_id,
            tenant_id=self.tenant_id,
            logger=self.logger,
            conn=self.conn,
        )
        self.dataframe_preparer = DataFramePreparer(logger=self.logger)
        self.cutoff_manager = cutoff_manager or CutoffManager(
            logger=self.logger,
            client_id=self.client_id,
            tenant_id=self.tenant_id,
            epc_id=self.epc_id,
            conn=self.conn,
        )
    
    def computations_for_one_pager(
        self,
        df: pd.DataFrame,
        tenant_id: int,
        label: str,
    ) -> Dict[str, Any]:
        """
        Prepare dataframe and compute all metrics needed for one-pager report.
        
        Based on the logic from reporting.py _prepare_dataframe and metric computations.
        
        Args:
            df: Prepared DataFrame with time features and cutoff month column
            tenant_id: Tenant ID
            label: Label for the tenant
            
        Returns:
            Dictionary containing:
            - df: Prepared DataFrame
            - tenant_id: Tenant ID
            - label: Label for the tenant
            - df_daily: Daily aggregated DataFrame
            - df_hourly: Hourly aggregated DataFrame
            - df_monthly: Monthly aggregated DataFrame
            - df_night: Nighttime consumption DataFrame
            - df_day: Daytime consumption DataFrame
            - df_weekdays: Weekday consumption DataFrame
            - df_weekends: Weekend consumption DataFrame
            - df_avg_hourly_consumption: Average hourly consumption DataFrame
            - df_avg_daily_consumption: Average daily consumption DataFrame
            - df_power_analysis: Power analysis DataFrame
            - last_month: Last month string (YYYY-MM)
            - load_energy_col: Selected load energy column name
            - load_power_col: Selected load power column name
            - kpis: Dictionary of KPI metrics
            - power_metrics: Dictionary of power metrics
            - time_consumption: Dictionary of time-based consumption metrics
        """
        try:
            self.logger.debug("🔍 Starting computations for one-pager")
            self.logger.debug(f"Using all available data for one-pager. Shape: {df.shape}")
            

            last_month = self.cutoff_manager.extract_last_month(df)
            mask = df['Year-Month-cut-off'] == last_month
            date_series = pd.to_datetime(df.loc[mask, "Date"], errors="coerce")
            if not date_series.empty:
                date_min = date_series.min()
                date_max = date_series.max()
                date_range = f"{date_min:%B %d, %Y} - {date_max:%B %d, %Y}"
            else:
                date_range = ""
            # Compute energy
            df = self.computations.compute_energy(df)
        
            
            # Prepare aggregated tables
            (df_daily, df_hourly, df_monthly, df_night, df_day, 
             df_weekdays, df_weekends, df_avg_hourly_consumption, 
             df_avg_daily_consumption) = self.computations.prepare_aggregated_tables(df)
            
            # Compute power analysis
            df_power_analysis = self.computations.compute_peak_power_and_always_on_power(df)
            
            
            # Compute metrics
            kpis = self.computations.compute_kpis(
                df_monthly, last_month, tenant_id=tenant_id
            )
            power_metrics = self.computations.compute_power_metrics(
                df_power_analysis, last_month, tenant_id=tenant_id
            )
            time_consumption = self.computations.compute_time_based_consumption(
                df_weekdays, df_weekends, df_day, df_night, last_month, tenant_id=tenant_id
            )
            
            self.logger.debug("✅ Computations for one-pager completed successfully")
            
            return {
                'df': df,
                'tenant_id': tenant_id,
                'label': label,
                'df_daily': df_daily,
                'df_hourly': df_hourly,
                'df_monthly': df_monthly,
                'df_night': df_night,
                'df_day': df_day,
                'df_weekdays': df_weekdays,
                'df_weekends': df_weekends,
                'df_avg_hourly_consumption': df_avg_hourly_consumption,
                'df_avg_daily_consumption': df_avg_daily_consumption,
                'df_power_analysis': df_power_analysis,
                'last_month': last_month,
                'kpis': kpis,
                'power_metrics': power_metrics,
                'time_consumption': time_consumption,
                'date_range': date_range,
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error in computations_for_one_pager: {e}")
            raise
    



# ============================================================================
# Export all classes
# ============================================================================

__all__ = [
    'Computations',
    'ElectricityAnalysisOrchestrator',
]

