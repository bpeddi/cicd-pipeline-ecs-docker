
from globalconfig import default_region


## Devops Account
devops_account = { "account": '567311256374', "region": default_region }

## CI/CD managed Accounts
managed_accounts = {
    "dev" : {
        "ingestion": {
            "account": '659300517259', "region": default_region, "enabled": True
        },
        "datalake": {
            "account": '232351851823', "region": default_region, "enabled": True
        },
        "consumer": {
            "account": '248877539307', "region": default_region, "enabled": True
        }
    },
    "stage" : {
        "ingestion": {
            "account": '111111111111', "region": default_region, "enabled": False
        },
        "datalake": {
            "account": '222222222222', "region": default_region, "enabled": False
        },
        "consumer": {
            "account": '333333333333', "region": default_region, "enabled": False
        }
    },
    "prod" : {
        "ingestion": {
            "account": '111111111111', "region": default_region, "enabled": False
        },
        "datalake": {
            "account": '222222222222', "region": default_region, "enabled": False
        },
        "consumer": {
            "account": '333333333333', "region": default_region, "enabled": False
        }
    },
}