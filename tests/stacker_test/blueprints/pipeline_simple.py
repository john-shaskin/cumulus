import troposphere
from cumulus.steps.storage.s3bucket import S3Bucket
from stacker.blueprints.base import Blueprint
import troposphere.codebuild

from cumulus.chain import chain, chaincontext
from cumulus.steps.dev_tools import pipeline, code_build_action, pipeline_stage, pipeline_source_action, lambda_action
from cumulus.steps.dev_tools.approval_action import ApprovalAction


class PipelineSimple(Blueprint):
    """
    An example dev_tools that doesn't do anything interesting.
    """

    VARIABLES = {
        # 'git-commit': {'type': basestring, 'description': 'git version'},
    }

    def create_template(self):
        t = self.template
        t.add_description("Acceptance Tests for cumulus pipelines")

        instance = self.name + self.context.environment['env']

        # TODO: give to builder
        the_chain = chain.Chain()
        # bucket becomes: cumulus-acceptance-tests-123123-namespace
        pipeline_bucket_name = troposphere.Join('', [
            self.context.namespace,
            "-",
            troposphere.Ref("AWS::AccountId"),
            "-",
            "automatedtests"
        ])

        bucket = S3Bucket(
            logical_name="PipelineBucket",
            bucket_name=pipeline_bucket_name,
        )
        # expected
        # cumulus-acc-964705782699-automatedtests
        # actual
        # acc-964705782699-automatedtests

        the_chain.add(bucket)

        the_pipeline = pipeline.Pipeline(
            name=self.name,
            bucket_name=pipeline_bucket_name,
            create_bucket=False,
        )

        the_chain.add(the_pipeline)

        source_stage_name = "SourceStage"
        deploy_stage_name = "DeployStage"
        service_artifact = "ServiceArtifact"

        the_chain.add(
            pipeline_stage.PipelineStage(stage_name=source_stage_name)
        )

        the_chain.add(
            pipeline_source_action.PipelineSourceAction(
                action_name="MicroserviceSource",
                output_artifact_name=service_artifact,
                s3_bucket_name=pipeline_bucket_name,
                s3_object_key="artifact.zip"
            )
        )

        the_chain.add(
            pipeline_stage.PipelineStage(
                stage_name=deploy_stage_name,
            ),
        )

        inline_ls_url_spec = """version: 0.2
phases:
  build:
    commands:
      - ls -lah
      - env
      - curl $URL
"""

        test_env = troposphere.codebuild.Environment(
            ComputeType='BUILD_GENERAL1_SMALL',
            Image='aws/codebuild/golang:1.10',
            Type='LINUX_CONTAINER',
            EnvironmentVariables=[
                {'Name': 'URL', 'Value': "https://google.ca"}
            ],
        )

        deploy_test = code_build_action.CodeBuildAction(
            prefix="test",
            stack_namespace="MyPipeline",
            action_name="DeployMyStuff",
            stage_name_to_add=deploy_stage_name,
            input_artifact_name=service_artifact,
            environment=test_env,
            buildspec=inline_ls_url_spec,
        )

        the_chain.add(deploy_test)

        lambda1 = lambda_action.LambdaAction(
            action_name="TriggerLambda",
            input_artifact_name=service_artifact,  # TODO make optional ?
            stage_name_to_add=deploy_stage_name,
            function_name="bswift-mock-function-mock-createUser"
        )

        the_chain.add(lambda1)

        # the_chain.add(code_build_action.CodeBuildAction(
        #     action_name="NotificationSmokeTest",
        #     stage_name_to_add=deploy_stage_name,
        #     input_artifact_name=service_artifact,
        #     environment=test_env,
        #     buildspec='buildspec_smoke_test.yml',
        # ))

        # TODO: integration tests don't confirm the below.. yet.  Do it.
        destroy_stage_name = "EchoAURL"
        the_chain.add(
            pipeline_stage.PipelineStage(
                stage_name=destroy_stage_name,
            ),
        )

        the_chain.add(ApprovalAction(
            action_name="ApproveDestruction",
            stage_name_to_add=destroy_stage_name
        ))

        the_chain.add(code_build_action.CodeBuildAction(
            prefix="test",
            stack_namespace=troposphere.Ref("StackNameParam"),
            action_name="DestroyService",
            stage_name_to_add=destroy_stage_name,
            input_artifact_name=service_artifact,
        ))

        chain_context = chaincontext.ChainContext(
            template=t,
            instance_name=instance
        )

        the_chain.run(chain_context)
