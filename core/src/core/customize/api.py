from io import StringIO

import datarobot as dr
import pandas as pd
import requests


def download_registry_dataset_as_dataframe(dataset_id: str) -> pd.DataFrame:
    """
    Download a dataset from DataRobot as a pandas DataFrame using requests.

    Args:
        token: The DataRobot API token.
        dataset_id: The ID of the dataset to download.
    Returns:
        DataFrame containing the dataset.
    Raises:
        Exception if the request fails or the response is invalid.
    """
    base_url = dr.client.get_client().endpoint
    url = f"{base_url}/datasets/{dataset_id}/file/"
    headers = {
        "Authorization": f"Bearer {dr.client.get_client().token}",
        "accept": "*/*",
    }
    response = requests.get(url, headers=headers, stream=True)
    response.raise_for_status()
    csv_content = response.content.decode("utf-8")
    df = pd.read_csv(StringIO(csv_content))
    return df
