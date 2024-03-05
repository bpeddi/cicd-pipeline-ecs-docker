
from configs.globalconfig import default_region


## Devops Account
devops_account = { "account": '594801937661', "region": default_region }

## CI/CD managed Accounts
managed_accounts = {
    "dev" : {

            "enabled": True,
            "account": '594801937661', 
            "region": default_region, 
            "vpc_id": "vpc-c50f3bbf",
            "private_subnets": [ "subnet-8de942c0", "subnet-465ebb19" ],
  },
    "prod" : {

            "enabled": True,
            "account": '594801937661', 
            "region": default_region, 
            "vpc_id": "vpc-c50f3bbf",
            "private_subnets": [ "subnet-8de942c0", "subnet-465ebb19" ],

    },
}