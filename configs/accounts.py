
from configs.globalconfig import default_region


## Devops Account
devops_account = { "account": '567311256374', "region": default_region }

## CI/CD managed Accounts
managed_accounts = {
    "dev" : {
        "ingestion": {
            "enabled": True,
            "account": '659300517259', 
            "region": default_region, 
            "vpc_id": "vpc-0a3d0bf08036ea8ad",
            "private_subnets": [ "subnet-01146a6b1135d0730", "subnet-0dd1c427542c98928" ],
            "database_subnets": [ "subnet-062c4617a1a4fe77e", "subnet-08c112d242e531ba5" ],
        },
        "datalake": {
            "enabled": True,
            "account": '232351851823', 
            "region": default_region, 
            "vpc_id": "vpc-0d619b30b1b1a7d5d",
            "private_subnets": [ "subnet-0d74610f5afc452af", "subnet-0861cf1cdd11a238f" ],
            "database_subnets": [ "subnet-035594a067c6f24ca", "subnet-084601862baff95d1" ],

        },
        "consumer": {
            "enabled": True,
            "account": '248877539307', 
            "region": default_region, 
            "vpc_id": "vpc-0c56d93757e3e09d9",
            "private_subnets": [ "subnet-087cc18103d513e1d", "subnet-0e0ce9f09243e6e30" ],
            "database_subnets": [ "subnet-023f3ae3fb96ed77c", "subnet-016ca3319ba37a54c" ],
        }
    },
    "stage" : {
        "ingestion": {
            "enabled": True,
            "account": '399536370415', 
            "region": default_region, 
            "vpc_id": "vpc-0800e033adb7345a8",
            "private_subnets": [ "subnet-031bfed79ae10d607", "subnet-0dd28c752371698ee" ],
            "database_subnets": [ "subnet-0f090d336b925a08f", "subnet-04250fe703c275ede" ],
        },
        "datalake": {
            "enabled": True,
            "account": '497145807131', 
            "region": default_region, 
            "vpc_id": "vpc-0d0ce93c3dad427f1",
            "private_subnets": [ "subnet-0b59d8c1c43d71ddb", "subnet-0ae1b1f2a46ac2a8d" ],
            "database_subnets": [ "subnet-017cd909f6a8ff42f", "subnet-09aba4b84d837c121" ],
            
        },
        "consumer": {
            "enabled": True,
            "account": '027102085951', 
            "region": default_region, 
            "vpc_id": "vpc-0deb9caa4936f0829",
            "private_subnets": [ "subnet-0407c99282d8f3d68", "subnet-03aeea327d921c539" ],
            "database_subnets": [ "subnet-02744649d7b87d7bd", "subnet-0518fa695a922087a" ],
        }
    },
    "prod" : {
        "ingestion": {
            "enabled": True,
            "account": '206080505010', 
            "region": default_region, 
            "vpc_id": "vpc-033a67ffcf11f5e1a",
            "private_subnets": [ "subnet-02a91f663ba17d7f9", "subnet-078882a846cb8b627" ],
            "database_subnets": [ "subnet-04159fd3458a31d39", "subnet-0b0024d0d470732ad" ],
        },
        "datalake": {
            "enabled": True,
            "account": '104346584539', 
            "region": default_region, 
            "vpc_id": "vpc-098fc03f9fdeec2b9",
            "private_subnets": [ "subnet-040a77f7a10a5a0d3", "subnet-02d1bc7a97c56573b" ],
            "database_subnets": [ "subnet-0f7bfd06d02d3dcdc", "subnet-0dd2f6b6186481926" ],
            
        },
        "consumer": {
            "enabled": True,
            "account": '014179487318', 
            "region": default_region, 
            "vpc_id": "vpc-02abb152f33252cdc",
            "private_subnets": [ "subnet-0a95384cbf0584e94", "subnet-0bcffa72f21be4d5e" ],
            "database_subnets": [ "subnet-0cff3ce9ce51e8a01", "subnet-0853c56b60cc6be8d" ],
        }
    },
}