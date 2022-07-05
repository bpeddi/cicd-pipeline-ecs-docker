#!/usr/bin/env python3
import os

import aws_cdk as cdk
import configs.accounts as a
import configs.globalconfig as g
from cdk_nag import AwsSolutionsChecks
from cicd_pipelines.ingestion_infra_pipeline import IngestionInfraPipeline
from cicd_pipelines.datalake_infra_pipeline import DatalakeInfraPipeline
from cicd_pipelines.consumer_infra_pipeline import ConsumerInfraPipeline
from cicd_pipelines.choice_emr_pipeline import ChoiceEmrPipeline

app = cdk.App()

###
##  Ingestion account(s) pipelines
###

for env_name in ["dev", "stage", "prod"]:
    account_category="ingestion"
    if (a.managed_accounts[env_name][account_category]["enabled"]):
        
        IngestionInfraPipeline(app, env_name+"-ingestion-infra-pipeline",
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
            datalake_account=a.managed_accounts[env_name]["datalake"]["account"],
            )


###
##  Central Datalake account(s) pipelines
###

for env_name in ["dev", "stage", "prod"]:
    account_category="datalake"
    if (a.managed_accounts[env_name][account_category]["enabled"]):

        DatalakeInfraPipeline(app, env_name+"-datalake-infra-pipeline",
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
            ingestion_account=a.managed_accounts[env_name]["ingestion"]["account"],            
            )

###
##  Consumer account(s) pipelines
###

for env_name in ["dev", "stage", "prod"]:
    account_category="consumer"
    if (a.managed_accounts[env_name][account_category]["enabled"]):

        ConsumerInfraPipeline(app, env_name+"-consumer-infra-pipeline",
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


###
# Choice EMR pipeline in datalake account
###

for env_name in ["dev", "stage", "prod"]:
    account_category="datalake"
    if (a.managed_accounts[env_name][account_category]["enabled"]):
        
        ChoiceEmrPipeline(app, env_name+"-choice-emr-pipeline",
            env=cdk.Environment(account=a.devops_account["account"],region=a.devops_account["region"]),

            target_account=a.managed_accounts[env_name][account_category]["account"],
            target_region=a.managed_accounts[env_name][account_category]["region"],
            repo_name="aws-hdip-choice-emr-pipeline",
            branch=env_name,
            rprefix=g.rprefix,
            env_name=env_name,
            ssmpath='/' + env_name + '/datalake/',
            cicd_ssm_path=g.cicd_ssm_path,
            vpc_id=a.managed_accounts[env_name][account_category]["vpc_id"],
            private_subnets=a.managed_accounts[env_name][account_category]["private_subnets"],
            database_subnets=a.managed_accounts[env_name][account_category]["database_subnets"],
            glue_service_role_name=g.glue_service_role_prefix+env_name
            
            )





cdk.Aspects.of(app).add(AwsSolutionsChecks(verbose=True))
app.synth()
