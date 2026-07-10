import apiClient from "../apiClient";

export type DatabaseTables = Record<string, string>;
export type DatabaseSchemas = Record<string, string>;
type DatabaseTablesResponse = DatabaseTables | string[];

export const normalizeDatabaseTables = (
  tables: DatabaseTablesResponse,
): DatabaseTables => {
  if (Array.isArray(tables)) {
    return Object.fromEntries(tables.map((table) => [table, table]));
  }
  return tables;
};

export const getDatabaseSchemas = async ({
  signal,
}: {
  signal?: AbortSignal;
}): Promise<DatabaseSchemas> => {
  const { data } = await apiClient.get<DatabaseSchemas>(
    `/v1/database/schemas`,
    {
      signal,
    },
  );
  return data;
};

export const getDefaultSchema = async ({
  signal,
}: {
  signal?: AbortSignal;
}): Promise<string> => {
  const { data } = await apiClient.get<string>(`/v1/database/default-schema`, {
    signal,
  });
  return data;
};

export const getDatabaseTables = async ({
  schema,
  signal,
}: {
  schema?: string;
  signal?: AbortSignal;
}): Promise<DatabaseTables> => {
  const params = schema ? { schema } : {};
  const { data } = await apiClient.get<DatabaseTablesResponse>(
    `/v1/database/tables`,
    {
      params,
      signal,
    },
  );
  return normalizeDatabaseTables(data);
};

export const loadFromDatabase = async ({
  tableNames,
  schema,
  signal,
}: {
  tableNames: string[];
  schema?: string;
  signal?: AbortSignal;
}): Promise<string[]> => {
  const payload: { table_names: string[]; schema_name?: string } = {
    table_names: tableNames,
  };
  if (schema) {
    payload.schema_name = schema;
  }

  const { data } = await apiClient.post<string[]>(
    "/v1/database/select",
    payload,
    {
      signal,
    },
  );
  return data;
};
