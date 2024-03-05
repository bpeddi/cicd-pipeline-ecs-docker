#!/usr/bin/env python3
import os

import aws_cdk as cdk
import configs.accounts as a
import configs.globalconfig as g
from cicd_pipelines.web_infra_pipeline import webInfraPipeline


app = cdk.App()

###
##  web account(s) pipelines
###

for env_name in ["dev",  "prod"]:
    if (a.managed_accounts[env_name]["enabled"]):
        
        webInfraPipeline(app, env_name+"-web-infra-pipeline",
            env=cdk.Environment(account=a.devops_account["account"],region=a.devops_account["region"]),
            target_account=a.managed_accounts[env_name]["account"],
            target_region=a.managed_accounts[env_name]["region"],
            repo_name="mymlproject",
            branch=env_name,
            rprefix=g.rprefix,
            env_name=env_name,
            vpc_id=a.managed_accounts[env_name]["vpc_id"],
            private_subnets=a.managed_accounts[env_name]["private_subnets"],
            )

app.synth()
