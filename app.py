#!/usr/bin/env python3
import os

import aws_cdk as cdk
import accounts as a
import globalconfig as g
from cicd_pipelines.ingestion_infra_pipeline import IngestionInfraPipeline

app = cdk.App()

for env_name in ["dev", "stage", "prod"]:
    if (a.managed_accounts[env_name]["ingestion"]["enabled"]):

        IngestionInfraPipeline(app, env_name+"-ingestion-infra-pipeline",
            env=cdk.Environment(account=a.devops_account["account"],region=a.devops_account["region"]),

            target_account=a.managed_accounts[env_name]["ingestion"]["account"],
            target_region=a.managed_accounts[env_name]["ingestion"]["region"],
            repo_name="aws-hdip-ingestion-infra",
            branch=env_name,
            rprefix=g.rprefix,
            env_name=env_name,
            ssmpath='/' + env_name + '/datalake/',
            cicd_ssm_path=g.cicd_ssm_path,
            )

app.synth()
