# try:
#     #python 3
#     from unittest.mock import patch
# except:
#     #python 2
#     from mock import patch

import unittest

import troposphere
from troposphere import codepipeline, codebuild, s3

from cumulus.chain import chaincontext
from cumulus.steps.dev_tools import pipeline, code_build_action
from cumulus.steps.dev_tools.vpc_config import VpcConfig
from cumulus.util.template_query import TemplateQuery


class TestPipelineStep(unittest.TestCase):

    def setUp(self):
        self.context = chaincontext.ChainContext(
            template=troposphere.Template(),
            instance_name='justtestin',
        )
        self.environment = codebuild.Environment(
            ComputeType='BUILD_GENERAL1_SMALL',
            Image='aws/codebuild/python:2.7.12',
            Type='LINUX_CONTAINER',
            EnvironmentVariables=[
                {'Name': 'TEST_VAR', 'Value': 'demo'}
            ],
        )

    def tearDown(self):
        del self.context
    #
    # def test_pipeline_records_metadata(self):
    #     sut = pipeline.Pipeline(
    #         name='test', bucket_name='testbucket'
    #     )
    #     sut.handle(self.context)
    #     self.assertIsInstance(sut, step.Step)
    #     self.assertTrue(
    #         expr=(cumulus.steps.dev_tools.META_LAST_STAGE_OUTPUT in self.context.metadata),
    #         msg="Expected Pipeline would set output artifact"
    #     )

    def test_pipeline_has_two_stages(self):

        sut = pipeline.Pipeline(
            name='test',
            bucket_name='testbucket',
        )
        sut.handle(self.context)
        t = self.context.template

        pipelines = TemplateQuery.get_resource_by_type(t, codepipeline.Pipeline)
        self.assertTrue(len(pipelines), 1)

    def test_pipeline_creates_default_bucket(self):

        sut = pipeline.Pipeline(
            name='test',
            bucket_name='testbucket',
        )
        sut.handle(self.context)
        t = self.context.template

        the_bucket = TemplateQuery.get_resource_by_type(t, s3.Bucket)
        self.assertTrue(len(the_bucket), 1)

    def test_pipeline_uses_non_default_bucket(self):
        sut = pipeline.Pipeline(
            name='test',
            bucket_name='ahhjustbucket',
            create_bucket=False,
        )
        sut.handle(self.context)
        t = self.context.template

        the_bucket = TemplateQuery.get_resource_by_type(t, s3.Bucket)
        self.assertEqual(len(the_bucket), 0)

    #
    # def test_codebuild_should_add_stage(self):
    #
    #     sut = pipeline.Pipeline(
    #         name='test', bucket_name='testbucket', artifact_path='blah.zip'
    #     )
    #     sut.handle(self.context)
    #     t = self.context.template
    #
    #     codebuild = code_build_stage.CodeBuildStage()
    #     codebuild.handle(self.context)
    #
    #     found_pipeline = TemplateQuery.get_resource_by_type(t, codepipeline.Pipeline)[0]
    #     stages = found_pipeline.properties['Stages']
    #     self.assertTrue(len(stages) == 2, msg="Expected Code Build to add a stage to the dev_tools")

    def test_code_build_should_not_add_vpc_config(self):

        action = code_build_action.CodeBuildAction(
            prefix='test',
            action_name="Test",
            stage_name_to_add="the_stage",
            input_artifact_name="no-input",
            stack_namespace="unique-codebuild-project",
        )

        project = action.create_project(
            prefix='test',
            chain_context=self.context,
            codebuild_role_arn='dummy-role',
            codebuild_environment=self.environment,
            name='test',
        )

        self.assertNotIn('VpcConfig', project.to_dict())

    def test_code_build_should_add_vpc_config(self):

        action = code_build_action.CodeBuildAction(
            prefix='test',
            vpc_config=VpcConfig(
                vpc_id='dummy-vpc',
                subnets=[
                    'dummy-subnet1'
                ]
            ),
            action_name="testAction",
            stage_name_to_add="thestage",
            input_artifact_name="test-input",
            stack_namespace="unique-codebuild-project",
        )

        project = action.create_project(
            prefix='test',
            chain_context=self.context,
            codebuild_role_arn='dummy-role',
            codebuild_environment=self.environment,
            name='test',
        )

        self.assertIn('VpcConfig', project.properties)
