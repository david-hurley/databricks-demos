import requests
from dataclasses import dataclass
from datetime import datetime
from typing import List
from enum import Enum

class OperatingStatus(Enum):
    ALL = "ALL"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"
    SUSPENDED = "SUSPENDED"
    INACTIVE = "INACTIVE"


class AssetType(Enum):
    ALL = "ALL"
    SOURCE = "ACTIVE"
    SINK = "SINK"


@dataclass
class MeteredVolumeList:
    begin_date_utc: datetime
    begin_date_mpt: datetime
    metered_volume: float


@dataclass
class MeteredAssetList:
    asset_ID: str
    asset_class: str
    metered_volume_list: List[MeteredVolumeList]


@dataclass
class MeteredVolume:
    pool_participant_ID: str
    asset_list: List[MeteredAssetList]


@dataclass
class PoolPrice:
    begin_datetime_utc: datetime
    begin_datetime_mpt: datetime
    pool_price: float
    forecast_pool_price: float
    rolling_30day_avg: float


@dataclass
class SystemMarginalPrice:
    begin_datetime_utc: datetime
    end_datetime_utc: datetime
    begin_datetime_mpt: datetime
    end_datetime_mpt: datetime
    system_marginal_price: float
    volume: float


@dataclass
class AgentList:
    agent_ID: str
    agent_name: str


@dataclass
class PoolParticipant:
    pool_participant_name: str
    pool_participant_ID: str
    corporate_contact: str
    agent_list: List[AgentList]


@dataclass
class albertaInternalLoad:
    begin_datetime_utc: datetime
    begin_datetime_mpt: datetime
    alberta_internal_load: float
    forecast_alberta_internal_load: float


@dataclass
class GenerationData:
    fuel_type: str
    aggregated_maximum_capability: int
    aggregated_net_generation: int
    aggregated_dispatched_contingency_reserve: int


@dataclass
class InterchangeData:
    path: str
    actual_flow: int


@dataclass
class CurrentSupplyDemand:
    last_updated_datetime_utc: datetime
    last_updated_datetime_mpt: datetime
    total_max_generation_capability: int
    total_net_generation: int
    net_to_grid_generation: int
    net_actual_interchange: int
    alberta_internal_load: int
    contingency_reserve_required: int
    dispatched_contigency_reserve_total: int
    dispatched_contingency_reserve_gen: int
    dispatched_contingency_reserve_other: int
    lssi_armed_dispatch: int
    lssi_offered_volume: int
    generation_data_list: List[GenerationData]
    interchange_list: List[InterchangeData]


@dataclass
class Asset:
    asset_name: str
    asset_ID: str
    asset_type: str
    operating_status: str
    pool_participant_name: str
    pool_participant_ID: str
    net_to_grid_asset_flag: str
    asset_incl_storage_flag: str


class aeso:
    def __init__(self, api_key):
        self.api_root_uri = "https://apimgw.aeso.ca/public/"
        self.api_key = api_key
        self.header = {"API-KEY": "{}".format(self.api_key)}
        self.date_format = "%Y-%m-%d %H:%M"

    def __try_float(self, v):
        try:
            return float(v)
        except Exception:
            return None

    def __generate_api_uri(self, api_endpoint: str) -> str:
        return f"{self.api_root_uri}{api_endpoint}"

    def __submit_get_request(self, uri: str):
        resp = requests.get(uri, headers=self.header)
        return resp

    def __parse_pool_price(self, response: str) -> List[PoolPrice]:
        list_of_pool_prices: List[PoolPrice] = []
        for item in response:
            begin_datetime_utc = datetime.strptime(
                item["begin_datetime_utc"], self.date_format
            )
            begin_datetime_mpt = datetime.strptime(
                item["begin_datetime_mpt"], self.date_format
            )
            pool_price = item["pool_price"]
            forecast_pool_price = item["forecast_pool_price"]
            rolling_30day_avg = item["rolling_30day_avg"]

            pool_price_object: PoolPrice = PoolPrice(
                begin_datetime_utc=begin_datetime_utc,
                begin_datetime_mpt=begin_datetime_mpt,
                pool_price=self.__try_float(pool_price),
                forecast_pool_price=self.__try_float(forecast_pool_price),
                rolling_30day_avg=self.__try_float(rolling_30day_avg),
            )
            list_of_pool_prices.append(pool_price_object)
        return list_of_pool_prices

    def __parse_system_marginal_price(self, response: str) -> List[SystemMarginalPrice]:
        list_of_marginal_prices: List[SystemMarginalPrice] = []
        for item in response:
            begin_datetime_utc = datetime.strptime(
                item["begin_datetime_utc"], self.date_format
            )
            begin_datetime_mpt = datetime.strptime(
                item["begin_datetime_mpt"], self.date_format
            )
            end_datetime_utc = datetime.strptime(
                item["end_datetime_utc"], self.date_format
            )
            end_datetime_mpt = datetime.strptime(
                item["end_datetime_mpt"], self.date_format
            )
            system_marginal_price = item["system_marginal_price"]
            volume = item["volume"]

            system_marginal_price_object: SystemMarginalPrice = SystemMarginalPrice(
                begin_datetime_utc=begin_datetime_utc,
                begin_datetime_mpt=begin_datetime_mpt,
                end_datetime_utc=end_datetime_utc,
                end_datetime_mpt=end_datetime_mpt,
                system_marginal_price=self.__try_float(system_marginal_price),
                volume=self.__try_float(volume),
            )
            list_of_marginal_prices.append(system_marginal_price_object)
        return list_of_marginal_prices

    def __parse_metered_volume(self, response: str) -> List[MeteredVolume]:
        metered_volumes = []
        for participant in response:
            pool_assets = []
            for asset in participant["asset_list"]:
                meter_volume_list = []
                for metered_volume_asset in asset["metered_volume_list"]:
                    begin_date_utc = datetime.strptime(
                        metered_volume_asset["begin_date_utc"], self.date_format
                    )
                    begin_date_mpt = datetime.strptime(
                        metered_volume_asset["begin_date_mpt"], self.date_format
                    )
                    meter_volume_list_item = MeteredVolumeList(
                        begin_date_utc=begin_date_utc,
                        begin_date_mpt=begin_date_mpt,
                        metered_volume=metered_volume_asset["metered_volume"],
                    )
                    meter_volume_list.append(meter_volume_list_item)
                metered_pool_asset = MeteredAssetList(
                    asset_ID=asset["asset_ID"],
                    asset_class=asset["asset_class"],
                    metered_volume_list=meter_volume_list,
                )
                pool_assets.append(metered_pool_asset)
            pool_participant = MeteredVolume(
                pool_participant_ID=participant["pool_participant_ID"],
                asset_list=pool_assets,
            )
            metered_volumes.append(pool_participant)
        return metered_volumes

    def __parse_pool_participant_list(self, response: str) -> List[PoolParticipant]:
        pool_paticipant = []
        if response:
            for participant in response:
                agent_list = []
                if participant.get("agent_list") is not None:
                    agent_list = [
                        AgentList(**agent) for agent in participant["agent_list"]
                    ]
                participant_object = PoolParticipant(
                    pool_participant_name=participant["pool_participant_name"],
                    pool_participant_ID=participant["pool_participant_ID"],
                    corporate_contact=participant["corporate_contact"],
                    agent_list=agent_list,
                )
                pool_paticipant.append(participant_object)
        return pool_paticipant

    def __parse_alberta_internal_load(self, response: str) -> List[albertaInternalLoad]:
        list_internal_load: List[albertaInternalLoad] = []
        for item in response:
            begin_datetime_utc = datetime.strptime(
                item["begin_datetime_utc"], self.date_format
            )
            begin_datetime_mpt = datetime.strptime(
                item["begin_datetime_mpt"], self.date_format
            )
            alberta_internal_load = item["alberta_internal_load"]
            forecast_alberta_internal_load = item["forecast_alberta_internal_load"]

            load_object: albertaInternalLoad = albertaInternalLoad(
                begin_datetime_utc=begin_datetime_utc,
                begin_datetime_mpt=begin_datetime_mpt,
                alberta_internal_load=self.__try_float(alberta_internal_load),
                forecast_alberta_internal_load=self.__try_float(
                    forecast_alberta_internal_load
                ),
            )
            list_internal_load.append(load_object)
        return list_internal_load

    def __parse_asset_list(self, response: str) -> List[Asset]:
        asset_data_list = [Asset(**asset_data) for asset_data in response]
        return asset_data_list

    def __parse_current_supply_demand(self, response: str) -> CurrentSupplyDemand:
        generation_data_list = [
            GenerationData(**gen_data) for gen_data in response["generation_data_list"]
        ]
        interchange_list = [
            InterchangeData(**interchange)
            for interchange in response["interchange_list"]
        ]
        current_supply_demand: CurrentSupplyDemand = CurrentSupplyDemand(
            generation_data_list=generation_data_list,
            interchange_list=interchange_list,
            **{
                k: v
                for k, v in response.items()
                if k not in ["generation_data_list", "interchange_list"]
            },
        )
        current_supply_demand.last_updated_datetime_utc = datetime.strptime(
            current_supply_demand.last_updated_datetime_utc, self.date_format
        )
        current_supply_demand.last_updated_datetime_mpt = datetime.strptime(
            current_supply_demand.last_updated_datetime_mpt, self.date_format
        )
        return current_supply_demand

    def get_pool_price_report(self, start_date: str, end_date: str) -> List[PoolPrice]:
        pool_price_endpoint: str = (
            f"poolprice-api/v1.1/price/poolPrice?startDate={start_date}&endDate={end_date}"
        )
        url = self.__generate_api_uri(pool_price_endpoint)
        pool_price_resp = self.__submit_get_request(url)
        if pool_price_resp.status_code == 200:
            return self.__parse_pool_price(
                pool_price_resp.json()["return"]["Pool Price Report"]
            )
        else:
            raise ValueError(pool_price_resp.raise_for_status())

    def get_system_marginal_price(
        self, start_date: str, end_date: str
    ) -> List[SystemMarginalPrice]:
        system_marginal_price_endpoint: str = f"report/v1.1/price/systemMarginalPrice?startDate={start_date}&endDate={end_date}"
        url = self.__generate_api_uri(system_marginal_price_endpoint)
        resp = self.__submit_get_request(url)
        if resp.status_code == 200:
            return self.__parse_system_marginal_price(
                resp.json()["return"]["System Marginal Price Report"]
            )
        else:
            raise ValueError(resp.raise_for_status())

    def get_pool_participant_list(self, pool_participant_id: str):
        pool_participant_list_endpoint: str = (
            f"report/v1/poolparticipantlist?pool_participant_ID={pool_participant_id}"
        )
        url = self.__generate_api_uri(pool_participant_list_endpoint)
        pool_participant_list_resp = self.__submit_get_request(url)
        if pool_participant_list_resp.status_code == 200:
            return self.__parse_pool_participant_list(
                pool_participant_list_resp.json()["return"]
            )
        else:
            raise ValueError(pool_participant_list_resp.raise_for_status())

    def get_alberta_internal_load(
        self, start_date: str, end_date: str
    ) -> List[albertaInternalLoad]:
        alberta_internal_load_endpoint: str = f"report/v1/load/albertaInternalLoad?startDate={start_date}&endDate={end_date}"
        url = self.__generate_api_uri(alberta_internal_load_endpoint)
        alberta_internal_load_resp = self.__submit_get_request(url)
        if alberta_internal_load_resp.status_code == 200:
            return self.__parse_alberta_internal_load(
                alberta_internal_load_resp.json()["return"]["Actual Forecast Report"]
            )
        else:
            raise ValueError(alberta_internal_load_resp.raise_for_status())

    def get_current_supply_demand(self) -> CurrentSupplyDemand:
        current_supply_demand_endpoint: str = "report/v1/csd/summary/current"
        url = self.__generate_api_uri(current_supply_demand_endpoint)
        current_supply_demand_resp = self.__submit_get_request(url)
        current_supply_demand_data = current_supply_demand_resp.json()["return"]
        if current_supply_demand_resp.status_code == 200:
            return self.__parse_current_supply_demand(
                current_supply_demand_resp.json()["return"]
            )
        else:
            raise ValueError(current_supply_demand_resp.raise_for_status())

    def get_asset_list(
        self,
        asset_id: str = None,
        pool_participant_id: str = None,
        operating_status: OperatingStatus = OperatingStatus.ALL,
        asset_type: AssetType = AssetType.ALL,
    ) -> List[Asset]:
        asset_list_endpoint: str = f"report/v1/assetlist?operating_status={operating_status.name}&asset_type={asset_type.name}"
        if asset_id:
            asset_list_endpoint = asset_list_endpoint + f"&asset_ID={asset_id}"
        if pool_participant_id:
            asset_list_endpoint = (
                asset_list_endpoint + f"&pool_participant_ID={pool_participant_id}"
            )
        url = self.__generate_api_uri(asset_list_endpoint)
        asset_list_resp = self.__submit_get_request(url)
        if asset_list_resp.status_code == 200:
            return self.__parse_asset_list(asset_list_resp.json()["return"])
        else:
            raise ValueError(asset_list_resp.raise_for_status())

    def get_metered_volume(
        self,
        start_date: str,
        end_date: str,
        asset_id: str = None,
        pool_participant_id: str = None,
    ) -> MeteredVolume:
        metered_volume_endpoint: str = (
            f"report/v1/meteredvolume/details?startDate={start_date}&endDate={end_date}"
        )
        if asset_id:
            metered_volume_endpoint = metered_volume_endpoint + f"&asset_ID={asset_id}"
        if pool_participant_id:
            metered_volume_endpoint = (
                metered_volume_endpoint + f"&pool_participant_ID={pool_participant_id}"
            )

        url = self.__generate_api_uri(metered_volume_endpoint)
        resp = self.__submit_get_request(url)
        data = resp.json()["return"]
        if resp.status_code == 200:
            return self.__parse_metered_volume(resp.json()["return"])
        else:
            raise ValueError(resp.raise_for_status())