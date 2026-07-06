import json

from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat.chat_completion_user_message_param import (
    ChatCompletionUserMessageParam,
)

from core.analyst_db import AnalystDB, InternalDataSourceType, get_data_source_type
from core.customize.usecase.prompt.builder import IRefinerDataInfoMessageFactory


class RefinerDataInfoMessageFactory(IRefinerDataInfoMessageFactory):
    def __init__(self, analyst_db: AnalystDB, dataset_names: list[str]):
        self.analyst_db = analyst_db
        self.dataset_names = dataset_names

    async def set_data_info(self) -> None:
        await self._get_shape_and_sample_info()
        await self._get_dictionary_data()

    async def _get_shape_and_sample_info(self) -> None:
        all_shapes, all_samples = [], []
        for dataset_name in self.dataset_names:
            try:
                dataset = (
                    await self.analyst_db.get_cleansed_dataset(dataset_name)
                ).to_df()
            except Exception:
                dataset = (await self.analyst_db.get_dataset(dataset_name)).to_df()
            all_shapes.append(
                f"{dataset_name}: {dataset.shape[0]} rows x {dataset.shape[1]} columns"
            )
            # Limit sample to 10 rows
            sample_df = dataset.head(10)
            all_samples.append(f"{dataset_name}:\n{sample_df}")
        self.shape_info = "\n".join(all_shapes)
        self.sample_data = "\n\n".join(all_samples)

    async def _get_dictionary_data(self) -> dict[str, list[str]]:
        all_columns = []
        all_descriptions = []
        all_data_types = []
        dictionaries = [
            await self.analyst_db.get_data_dictionary(name)
            for name in self.dataset_names
        ]
        for dictionary in dictionaries:
            if dictionary is None:
                continue
            for entry in dictionary.column_descriptions:
                all_columns.append(f"{dictionary.name}.{entry.column}")
                all_descriptions.append(entry.description)
                all_data_types.append(entry.data_type)

        # Create dictionary format for prompt
        dictionary_data = {
            "columns": all_columns,
            "descriptions": all_descriptions,
            "data_types": all_data_types,
        }
        self.dictionary_data = dictionary_data

    async def build_dictionary_data(self) -> ChatCompletionMessageParam:
        return ChatCompletionUserMessageParam(
            role="user",
            content=f"Data Dictionary:\n{json.dumps(self.dictionary_data, ensure_ascii=False)}",
        )

    async def build_data_shape_info(self) -> ChatCompletionMessageParam:
        return ChatCompletionUserMessageParam(
            role="user", content=f"Dataset Shapes:\n{self.shape_info}"
        )

    async def build_sample_data_info(self) -> ChatCompletionMessageParam:
        return ChatCompletionUserMessageParam(
            role="user", content=f"Dataset Samples:\n{self.sample_data}"
        )


async def get_datasets_names(data_source: str, analyst_db: AnalystDB) -> list[str]:
    # data_source に基づいてデータセット名を取得するロジックを実装
    source = get_data_source_type(data_source)
    dataset_metadata = []
    if source in [InternalDataSourceType.REGISTRY, InternalDataSourceType.FILE]:
        dataset_metadata = (
            await analyst_db.list_analyst_dataset_metadata(
                InternalDataSourceType.REGISTRY
            )
        ) + (
            await analyst_db.list_analyst_dataset_metadata(InternalDataSourceType.FILE)
        )
    else:
        dataset_metadata = await analyst_db.list_analyst_dataset_metadata(source)
    datasets_names = [
        ds.name for ds in dataset_metadata
    ]  # 例: "catalog", "database", "registry" など

    return datasets_names
