import { DictionaryTable } from './types';
import loader from '@/assets/loader.svg';

export const getDictionariesMenu = (data: DictionaryTable[]) =>
  data?.map(dictionary => ({
    key: dictionary.name,
    name: dictionary.name,
    endIcon: dictionary.in_progress ? (
      <img src={loader} alt="processing" className="mr-2 w-4 h-4 animate-spin" />
    ) : undefined,
  }));
