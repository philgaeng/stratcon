# Database Loading Strategy Recommendation

## Recommendation: **Option 2 - Single DB Query + Pandas Aggregations**

### Why This Approach?

1. **Data Volume is Manageable**
   - Total database: ~1.4M consumption records
   - Single load report: ~50K-200K records (1-2 years at 15-min intervals)
   - Memory footprint: ~5-20MB per load (very manageable for pandas)

2. **Complex Time-Based Logic**
   - Cutoff months (spanning calendar months)
   - Weekday/weekend filtering
   - Hour-based filtering (daytime/nighttime: 9am-6pm, 10pm-5am)
   - Time-based features (Hour, DayOfWeek, etc.)
   - These are **much simpler** in pandas than complex SQL

3. **Existing Code Structure**
   - `_prepare_dataframe()` already does all aggregations in pandas
   - Minimal refactoring needed
   - Easier to test and debug

4. **Flexibility**
   - Same code works for single load, building, or client reports
   - Easy to add new metrics without changing DB queries
   - Can handle different date ranges dynamically

5. **Performance**
   - Single round trip to database
   - Pandas aggregations are highly optimized
   - SQLite can efficiently filter by load_id and date range

### Implementation Approach

#### For Single Load Reports:
```python
# Single query: get all timestamps for the load
SELECT timestamp, load_kW 
FROM consumptions 
WHERE load_id = ? 
  AND timestamp >= ? 
  AND timestamp <= ?
ORDER BY timestamp
```

#### For Multi-Load Reports (Building/Client):
```python
# Option A: Multiple loads, one query
SELECT timestamp, load_id, load_name, load_kW 
FROM consumptions 
WHERE load_id IN (?, ?, ...)
  AND timestamp >= ? 
  AND timestamp <= ?
ORDER BY timestamp, load_id

# Then aggregate by timestamp in pandas (sum all loads per timestamp)
# This gives you the "building total" or "client total" for each timestamp
```

### Code Structure

```python
def _load_data_from_db(
    load_id: Optional[int],
    load_ids: Optional[List[int]],  # For multi-load
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    logger: ReportLogger
) -> pd.DataFrame:
    """
    Load consumption data from database.
    
    Returns DataFrame with columns: timestamp, load_kW (and load_id, load_name for multi-load)
    """
    conn = get_db_connection()
    
    if load_ids:
        # Multi-load: building or client report
        placeholders = ','.join(['?'] * len(load_ids))
        query = f"""
            SELECT c.timestamp, c.load_id, l.load_name, c.load_kW
            FROM consumptions c
            JOIN loads l ON c.load_id = l.id
            WHERE c.load_id IN ({placeholders})
        """
        params = list(load_ids)
    else:
        # Single load
        query = """
            SELECT timestamp, load_kW
            FROM consumptions
            WHERE load_id = ?
        """
        params = [load_id]
    
    # Add date filtering if provided
    if start_date:
        query += " AND timestamp >= ?"
        params.append(start_date)
    if end_date:
        query += " AND timestamp <= ?"
        params.append(end_date)
    
    query += " ORDER BY timestamp"
    
    df = pd.read_sql_query(query, conn, params=params, parse_dates=['timestamp'])
    
    # For multi-load: aggregate by timestamp (sum all loads)
    if load_ids:
        df = df.groupby('timestamp')['load_kW'].sum().reset_index()
        df['load_name'] = 'Combined Loads'  # Or derive from load_ids
    
    # Set timestamp as index (matching current CSV structure)
    df.set_index('timestamp', inplace=True)
    df.sort_index(inplace=True)
    
    return df
```

### Hybrid Optimization for Large Multi-Load Scenarios

For building/client reports with **many loads** (>10), you could do a hybrid:

1. **SQL aggregation by timestamp** (sum all loads per timestamp):
```sql
SELECT timestamp, SUM(load_kW) as load_kW
FROM consumptions
WHERE load_id IN (?, ?, ...)
GROUP BY timestamp
ORDER BY timestamp
```

2. **Then use existing pandas aggregation** for time-based logic

This reduces data volume for very large multi-load scenarios while keeping the flexibility.

### Performance Considerations

#### Current Performance (Estimated):
- Single load query: ~50-200ms (SQLite)
- Pandas aggregation: ~100-500ms
- **Total: ~150-700ms per report** ✅

#### If Performance Becomes an Issue:
1. **Add indexes** (already done on timestamp, load_id)
2. **Add date range filtering** (limit to last 2 years by default)
3. **Cache aggregated results** (Redis/Memcached for common queries)
4. **Materialized views** for monthly aggregations (pre-compute monthly totals)

### Migration Path

1. **Phase 1**: Replace `load_and_prepare_data()` to read from DB instead of CSV
2. **Phase 2**: Keep all existing pandas aggregation code unchanged
3. **Phase 3**: Test and optimize based on real usage patterns

### Conclusion

**Go with Option 2** - It's simpler, more flexible, and performs well for your data volume. The complex time-based aggregations are much easier to maintain in pandas than in SQL, and you already have working code for this.

The hybrid approach (SQL aggregation for multi-load) can be added later if needed, but start simple with single-query approach.

