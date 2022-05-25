#!/usr/bin/env python3
import os

import aws_cdk as cdk
import configs.accounts as a
import configs.globalconfig as g
from cdk_nag import AwsSolutionsChecks
from cicd_pipelines.ingestion_infra_pipeline import InfraPipeline

app = cdk.App()

###
##  Ingestion account(s) pipelines
###

for env_name in ["dev", "stage", "prod"]:
    account_category="ingestion"
    if (a.managed_accounts[env_name][account_category]["enabled"]):
        
        InfraPipeline(app, env_name+"-ingestion-infra-pipeline",
            env=cdk.Environment(account=a.devops_account["account"],region=a.devops_account["region"]),

            target_account=a.managed_accounts[env_name][account_category]["account"],
            target_region=a.managed_accounts[env_name][account_category]["region"],
            repo_name="aws-hdip-ingestion-infra",
            branch=env_name,
            rprefix=g.rprefix,
            env_name=env_name,
            ssmpath='/' + env_name + '/datalake/',
            cicd_ssm_path=g.cicd_ssm_path,
            vpc_id=a.managed_accounts[env_name][account_category]["vpc_id"],
            private_subnets=a.managed_accounts[env_name][account_category]["private_subnets"],
            database_subnets=a.managed_accounts[env_name][account_category]["database_subnets"],
            )


###
##  Central Datalake account(s) pipelines
###

for env_name in ["dev", "stage", "prod"]:
    account_category="datalake"
    if (a.managed_accounts[env_name][account_category]["enabled"]):

        InfraPipeline(app, env_name+"-datalake-infra-pipeline",
            env=cdk.Environment(account=a.devops_account["account"],region=a.devops_account["region"]),

            target_account=a.managed_accounts[env_name][account_category]["account"],
            target_region=a.managed_accounts[env_name][account_category]["region"],
            repo_name="aws-hdip-datalake-infra",
            branch=env_name,
            rprefix=g.rprefix,
            env_name=env_name,
            ssmpath='/' + env_name + '/datalake/',
            cicd_ssm_path=g.cicd_ssm_path,
            vpc_id=a.managed_accounts[env_name][account_category]["vpc_id"],
            private_subnets=a.managed_accounts[env_name][account_category]["private_subnets"],
            database_subnets=a.managed_accounts[env_name][account_category]["database_subnets"],
            )

###
##  Ingestion account(s) pipelines
###

for env_name in ["dev", "stage", "prod"]:
    account_category="consumer"
    if (a.managed_accounts[env_name][account_category]["enabled"]):

        InfraPipeline(app, env_name+"-consumer-infra-pipeline",
            env=cdk.Environment(account=a.devops_account["account"],region=a.devops_account["region"]),

            target_account=a.managed_accounts[env_name][account_category]["account"],
            target_region=a.managed_accounts[env_name][account_category]["region"],
            repo_name="aws-hdip-consumer-infra",
            branch=env_name,
            rprefix=g.rprefix,
            env_name=env_name,
            ssmpath='/' + env_name + '/datalake/',
            cicd_ssm_path=g.cicd_ssm_path,
            vpc_id=a.managed_accounts[env_name][account_category]["vpc_id"],
            private_subnets=a.managed_accounts[env_name][account_category]["private_subnets"],
            database_subnets=a.managed_accounts[env_name][account_category]["database_subnets"],
            )

cdk.Aspects.of(app).add(AwsSolutionsChecks(verbose=True))
app.synth()
