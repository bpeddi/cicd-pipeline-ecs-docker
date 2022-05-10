import aws_cdk as core
import aws_cdk.assertions as assertions

from aws_hdip_cicd_pipelines.aws_hdip_cicd_pipelines_stack import AwsHdipCicdPipelinesStack

# example tests. To run these tests, uncomment this file along with the example
# resource in aws_hdip_cicd_pipelines/aws_hdip_cicd_pipelines_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = AwsHdipCicdPipelinesStack(app, "aws-hdip-cicd-pipelines")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
