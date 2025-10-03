export const databaseKeys = {
  all: ['database'] as const,
  schemas: () => [...databaseKeys.all, 'schemas'] as const,
  defaultSchema: () => [...databaseKeys.all, 'default-schema'] as const,
  tables: (schema?: string) => [...databaseKeys.all, 'tables', schema] as const,
};
