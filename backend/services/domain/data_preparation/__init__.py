#!/usr/bin/env python3
"""
Data Preparation Module

This module provides classes and functions for loading and preparing data for analysis.
"""

# Import classes
from backend.services.domain.data_preparation.cutoff_manager import CutoffManager
from backend.services.domain.data_preparation.dataframe_preparer import DataFramePreparer

from datetime import datetime
from typing import Optional, List
import pandas as pd
import os
import sqlite3
from backend.services.core.utils import ReportLogger
from backend.services.core.base import ServiceContext


# ============================================================================
# Context-aware Orchestrator Class
# ============================================================================

class DataPreparationOrchestrator(ServiceContext):
    """
    Orchestrates data loading and preparation with shared context.
    
    Holds user_id, client_id, and manages shared resources like default_values_dict.
    Instantiate once per request/session from frontend context.
    
    Usage:
        # In your API endpoint/request handler:
        orchestrator = DataPreparationOrchestrator(
            user_id=request.user_id,      # From frontend context
            client_id=request.client_id,  # From frontend context
            logger=logger,
            conn=db_conn                  # Optional: share connection
        )
        
        # Now all operations share context:
        df, loads, _, _ = orchestrator.load_and_prepare_data(load_ids=[1, 2, 3])
        
        # default_values_dict is automatically available and cached:
        # orchestrator.cutoff_manager.cutoff_default_values_dict
    """
    
    def __init__(
        self,
        user_id: Optional[int] = None,
        client_id: Optional[int] = None,
        tenant_id: Optional[int] = None,
        logger: Optional[ReportLogger] = None,
        conn: Optional[sqlite3.Connection] = None,
    ):
        """
        Initialize orchestrator with user context.
        
        Args:
            user_id: User ID from frontend context
            client_id: Client ID from frontend context
            logger: Logger instance
            conn: Optional database connection (shared across operations)
        """
        super().__init__(
            user_id=user_id,
            client_id=client_id,
            tenant_id=tenant_id,
            logger=logger,
            conn=conn,
        )
        
        # Initialize component classes with shared context
        self.cutoff_manager = CutoffManager(
            logger=self.logger,
            client_id=self.client_id,
            tenant_id=self.tenant_id,
            epc_id=self.epc_id,
            conn=self.conn,
        )
        self.dataframe_preparer = DataFramePreparer(logger=self.logger)
        
        # default_values_dict will be lazily initialized when first accessed
        # via self.cutoff_manager.cutoff_default_values_dict
    


    def load_and_prepare_data_for_tenant(
        self,
        tenant_id: Optional[int],
        source: str = 'meter_records',
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        load_ids: Optional[List[int]] = None,
    ) -> pd.DataFrame:
        """
        Load electricity consumption data from database and prepare it for analysis.
        """
        try:
            tenant_id = tenant_id or (self.tenant_id or None)
            if not tenant_id:
                raise ValueError("tenant_id cannot be empty")

            df = self.db.load_power_data_for_tenant(
                tenant_id=tenant_id,
                start_date=start_date,
                end_date=end_date,
                conn=self.conn,
                logger=self.logger,
                load_ids=load_ids,
            )
            self.logger.debug("✅ Data loaded successfully from db!")
            self.logger.debug(f"Dataset shape: {df.shape}")
            if not df.empty:
                self.logger.debug(f"Date range: {df.index.min()} to {df.index.max()}")
            else:
                raise ValueError(f"❌ No data found for tenant_id={tenant_id}")

            df = df.reset_index().rename(columns={"index": "timestamp"})

            df = self.cutoff_manager.generate_cutoff_month_column_for_tenant(
                df, tenant_id, source=source
            )

            if df is None or df.empty:
                raise ValueError("No data found after cutoff month column generation")

            self.logger.debug("✅ Cutoff month column generated successfully!")
            self.logger.debug(f"Dataset shape: {df.shape if df is not None else 'None'}")

            if "Year-Month-cut-off" not in df.columns:
                df["Year-Month-cut-off"] = pd.to_datetime(df["timestamp"]).dt.to_period("M").astype(str)

            df.set_index("timestamp", inplace=True)

            df = self.dataframe_preparer.add_time_features(df)
            self.logger.debug("✅ Time-based features added successfully!")

            df_selected = self.dataframe_preparer.select_full_months(df, warning_only=True)
            if df_selected is None or df_selected.empty:
                self.logger.warning("⚠️ No complete months found; proceeding with available data.")
                df_selected = df
            df = df_selected

            self.logger.debug(f"Using all available data for one-pager. Shape: {df.shape}")
            return df
        except Exception as exc:
            self.logger.error(f"❌ Error loading data: {exc}")
            raise


# ============================================================================
# Export all classes
# ============================================================================

__all__ = [
    'CutoffManager',
    'DataFramePreparer',
    'DataPreparationOrchestrator',
]
