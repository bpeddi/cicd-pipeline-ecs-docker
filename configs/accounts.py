from configs.globalconfig import default_region


## Devops Account
devops_account = {"account": "XXXXXXX", "region": default_region}

## CI/CD managed Accounts
managed_accounts = {
    "baladev": {
        "enabled": True,
        "account": "XXXXXXX",
        "region": default_region,
        "vpc_id": "vpc-c50f3bbf",
        "private_subnets": ["subnet-8de942c0", "subnet-465ebb19"],
        "artifacts_bucket": "aws-vamsi-devops-artifacts-bucket",
    },
    "prod": {
        "enabled": True,
        "account": "XXXXXXX",
        "region": default_region,
        "vpc_id": "vpc-c50f3bbf",
        "private_subnets": ["subnet-8de942c0", "subnet-465ebb19"],
        "artifacts_bucket": "aws-vamsi-prod-devops-artifacts-bucket",
    },
}
