import awacs
import troposphere

import cumulus.policies
import cumulus.policies.cloudformation
import cumulus.types.codebuild.buildaction # TODO: Should the codebuild folder be dev_tools?

from troposphere import iam, codepipeline, Ref, Sub
from stacker.blueprints.variables.types import CFNString
from cumulus.chain import step
from cumulus.steps.dev_tools import META_PIPELINE_BUCKET_POLICY_REF, \
    META_PIPELINE_BUCKET_REF


class CloudFormationAction(step.Step):

    VARIABLES = {
        'TemplateFileName': {
            'type': CFNString,
            'description': 'Name of the template file, within the input artifact'
        },
        'TemplateConfigurationFileName': {
            'type': CFNString,
            'description': 'Name of the template configuration file, within the input artifact'
        }
    }

    def __init__(self,
                 action_name,
                 input_artifact_name,
                 stage_name_to_add,
                 stack_name):
        """
        :type action_name: basestring Displayed on the console
        """
        step.Step.__init__(self)
        self.action_name = action_name
        self.input_artifact_name = input_artifact_name
        self.stage_name_to_add = stage_name_to_add
        self.stack_name = stack_name

    def handle(self, chain_context):

        print("Adding action %sstage" % self.action_name)

        policy_name = "CloudFormationPolicy%stage" % chain_context.instance_name
        role_name = "CloudFormationRole%stage" % self.action_name

        # TODO: Create proper role for Cloudformation deploy
        cloud_formation_role = iam.Role(
            role_name,
            Path="/",
            AssumeRolePolicyDocument=awacs.aws.Policy(
                Statement=[
                    awacs.aws.Statement(
                        Effect=awacs.aws.Allow,
                        Action=[awacs.sts.AssumeRole],
                        Principal=awacs.aws.Principal(
                            'Service',
                            "cloudformation.amazonaws.com"
                        )
                    )]
            ),
            Policies=[
                cumulus.policies.cloudformation.get_policy_cloudformation_general_access(policy_name)
            ],
            ManagedPolicyArns=[
                chain_context.metadata[META_PIPELINE_BUCKET_POLICY_REF]
            ]
        )

        cloud_formation_action = cumulus.types.codebuild.buildaction.CloudFormationAction(
            Name=self.action_name,
            InputArtifacts=[
                codepipeline.InputArtifacts(Name=self.input_artifact_name)
            ],
            Configuration={
                'ActionMode': 'CREATE_OR_REPLACE', #TODO: Configurable?
                'RoleArn': Ref(cloud_formation_role),
                'StackName': self.stack_name,
                'TemplateConfiguration': Sub('TemplateSource::${TemplateConfigurationFileName}'),
                'TemplatePath': Sub("TemplateSource::${TemplateFileName}")
            },
            RunOrder="1"
        )

        chain_context.template.add_resource(cloud_formation_role)
        
        stage = cumulus.util.tropo.TemplateQuery.get_pipeline_stage_by_name(
            template=chain_context.template,
            stage_name=self.stage_name_to_add
        )

        # TODO accept a parallel action to the previous action, and don't +1 here.
        next_run_order = len(stage.Actions) + 1
        cloud_formation_action.RunOrder = next_run_order
        stage.Actions.append(cloud_formation_action)
