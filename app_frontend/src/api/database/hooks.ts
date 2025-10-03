import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { databaseKeys } from './keys';
import { getDatabaseSchemas, getDatabaseTables, loadFromDatabase, getDefaultSchema } from './api-requests';
import { dictionaryKeys } from '../dictionaries/keys';
import { DictionaryTable } from '../dictionaries/types';

export const useGetDatabaseSchemas = () => {
  const queryResult = useQuery({
    queryKey: databaseKeys.schemas(),
    queryFn: ({ signal }) => getDatabaseSchemas({ signal }),
  });

  return queryResult;
};

export const useGetDefaultSchema = () => {
  const queryResult = useQuery({
    queryKey: databaseKeys.defaultSchema(),
    queryFn: ({ signal }) => getDefaultSchema({ signal }),
  });

  return queryResult;
};

export const useGetDatabaseTables = (schema?: string) => {
  const queryResult = useQuery({
    queryKey: databaseKeys.tables(schema),
    queryFn: ({ signal }) => getDatabaseTables({ schema, signal }),
  });

  return queryResult;
};

export const useLoadFromDatabaseMutation = ({
  onSuccess,
  onError,
}: {
  onSuccess: (data: unknown) => void;
  onError: (error: Error) => void;
}) => {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: ({ tableNames, schema }: { tableNames: string[]; schema?: string }) =>
      loadFromDatabase({
        tableNames,
        schema,
      }),
    onMutate: async () => {
      const previousDictionaries =
        queryClient.getQueryData<DictionaryTable[]>(dictionaryKeys.all) || [];
      return { previousDictionaries };
    },
    onSuccess: data => {
      queryClient.invalidateQueries({ queryKey: dictionaryKeys.all });
      onSuccess(data);
    },
    onError: (error, _, context) => {
      if (context?.previousDictionaries) {
        queryClient.setQueryData<DictionaryTable[]>(
          dictionaryKeys.all,
          context.previousDictionaries
        );
      }
      onError(error);
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: databaseKeys.all });
    },
  });

  return mutation;
};
