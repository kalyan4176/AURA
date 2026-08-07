import React, { useMemo } from 'react';
import { AgGridReact } from 'ag-grid-react';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';

/**
 * Enterprise Tabular Data Grid Wrapper using AG Grid.
 * Built for high-performance virtualization of millions of cells.
 */
export function DataGrid({ columns = [], rows = [], height = '400px' }) {
  // Map AURA column metadata to AG Grid columns
  const columnDefs = useMemo(() => {
    return columns.map((col) => ({
      field: col.name,
      headerName: col.name,
      sortable: true,
      filter: true,
      resizable: true,
      flex: 1,
      minWidth: 120,
      valueFormatter: (params) => {
        if (params.value === null || params.value === undefined) {
          return '-';
        }
        return String(params.value);
      },
    }));
  }, [columns]);

  const defaultColDef = useMemo(() => ({
    sortable: true,
    filter: true,
    resizable: true,
  }), []);

  return (
    <div className="ag-theme-alpine-dark w-full overflow-hidden rounded-lg border border-border" style={{ height }}>
      <AgGridReact
        rowData={rows}
        columnDefs={columnDefs}
        defaultColDef={defaultColDef}
        pagination={true}
        paginationPageSize={10}
        paginationPageSizeSelector={[10, 20, 50]}
        domLayout="normal"
      />
    </div>
  );
}
export default DataGrid;
