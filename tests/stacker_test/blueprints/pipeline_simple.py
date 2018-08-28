import troposphere
from stacker.blueprints.base import Blueprint
import troposphere.codebuild

from cumulus.chain import chain, chaincontext
from cumulus.steps.development import pipeline, code_build_action, pipeline_stage, pipeline_source_action
from cumulus.steps.development.approval_action import ApprovalAction


class PipelineSimple(Blueprint):
    """
    An example development that doesn't do anything interesting.
    """

    VARIABLES = {
        # 'git-commit': {'type': basestring, 'description': 'git version'},
    }

    def create_template(self):

        t = self.template
        t.add_description("development spike for dtf")

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

        the_chain.add(pipeline.Pipeline(
            name=self.name,
            bucket_name=pipeline_bucket_name,
        ))

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
                s3_object_key="artifact.tar.gz"
            )
        )

        the_chain.add(
            pipeline_stage.PipelineStage(
                stage_name=deploy_stage_name,
            ),
        )

        the_chain.add(code_build_action.CodeBuildAction(
            action_name="DeployMyStuff",
            stage_name_to_add=deploy_stage_name,
            input_artifact_name=service_artifact,
        ))

        test_env = troposphere.codebuild.Environment(
            ComputeType='BUILD_GENERAL1_SMALL',
            Image='aws/codebuild/golang:1.10',
            Type='LINUX_CONTAINER',
            EnvironmentVariables=[
                {'Name': 'URL', 'Value': "https://google.ca"}
            ],
        )

        inline_echo_url_spec = """version: 0.2
        phases:
          build:
            commands:
               - echo $URL
                """

        the_chain.add(code_build_action.CodeBuildAction(
            action_name="NotificationSmokeTest",
            stage_name_to_add=deploy_stage_name,
            input_artifact_name=service_artifact,
            environment=test_env,
            buildspec='buildspec_smoke_test.yml',
        ))

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
            action_name="DestroyRocketChat",
            stage_name_to_add=destroy_stage_name,
            input_artifact_name=service_artifact,
            buildspec=inline_echo_url_spec,
        ))

        chain_context = chaincontext.ChainContext(
            template=t,
            instance_name=instance
        )

        the_chain.run(chain_context)
