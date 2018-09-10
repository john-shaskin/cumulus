import awacs
import awacs.aws
import awacs.ec2
import awacs.iam
import awacs.logs
import awacs.s3
import awacs.sts
from troposphere import iam, \
    codepipeline, Ref

import cumulus.policies
import cumulus.policies.codebuild
from cumulus.chain import step
from cumulus.steps.dev_tools import META_PIPELINE_BUCKET_POLICY_REF
from cumulus.types.codebuild.buildaction import SourceS3Action, SourceCodeCommitAction
from cumulus.util.tropo import TemplateQuery


class SourceActionCodeCommit(step.Step):

    def __init__(self,
                 action_name,
                 output_artifact_name,
                 ):
        """
        :type s3_object_key: basestring Path of the artifact in the bucket.
        :type s3_bucket_name: basestring or troposphere.Ref Object of the bucket name.
        :type input_artifact_name: basestring The artifact name in the pipeline.
              (should contain buildspec.yml. You can override that name in a codebuild action)
        :type action_name: basestring Displayed on the console
        :type environment: troposphere.codebuild.Environment Optional if you need ENV vars or a different build.
        :type vpc_config.Vpc_Config: Only required if the codebuild step requires access to the VPC
        """
        step.Step.__init__(self)
        self.output_artifact_name = output_artifact_name
        self.action_name = action_name

    def handle(self, chain_context):
        print("Adding source action %s." % self.action_name)

        policy_name = "CodeBuildPolicy%s" % chain_context.instance_name
        codebuild_policy = cumulus.policies.codebuild.get_policy_code_build_general_access(policy_name)

        role_name = "PipelineSourceRole%s" % self.action_name
        codebuild_role = iam.Role(
            role_name,
            Path="/",
            AssumeRolePolicyDocument=awacs.aws.Policy(
                Statement=[
                    awacs.aws.Statement(
                        Effect=awacs.aws.Allow,
                        Action=[awacs.sts.AssumeRole],
                        Principal=awacs.aws.Principal(
                            'Service',
                            "codebuild.amazonaws.com"
                        )
                    )]
            ),
            Policies=[
                codebuild_policy
            ],
            ManagedPolicyArns=[
                chain_context.metadata[META_PIPELINE_BUCKET_POLICY_REF]
            ]
        )

        source_action = SourceCodeCommitAction(
            Name=self.action_name,
            OutputArtifacts=[
                codepipeline.OutputArtifacts(
                    Name=self.output_artifact_name
                )
            ],
            # TODO: when parameters are figured out, inject tehm into the template here.
            Configuration={
                "RepositoryName": Ref("RepositoryName"),
                "BranchName": Ref("RepositoryBranch"),
            },
        )

        chain_context.template.add_resource(codebuild_role)

        found_pipelines = TemplateQuery.get_resource_by_type(
            template=chain_context.template,
            type_to_find=codepipeline.Pipeline)
        pipeline = found_pipelines[0]

        # Alternate way to get this
        # dummy = TemplateQuery.get_resource_by_title(chain_context.template, 'AppPipeline')

        stages = pipeline.Stages  # type: list

        # TODO: find stage by name
        first_stage = stages[0]

        # TODO accept a parallel action to the previous action, and don't +1 here.
        first_stage.Actions.append(source_action)
