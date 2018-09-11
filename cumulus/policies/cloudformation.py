import awacs
import awacs.aws
import awacs.logs
import awacs.iam
import awacs.s3
import awacs.ecr

from troposphere import iam


def get_policy_cloudformation_general_access(policy_name):
    # TODO: Return policy with permissions:
    # 1. Full Cloudformation access to stacks prefixed with application name
    # 2. IAM access (currently using unlimited access, but this seems like it could be limited a bit)
    return iam.Policy(
        PolicyName=policy_name,
        PolicyDocument=awacs.aws.PolicyDocument(
            Version="2012-10-17",
            Id="%sId" % policy_name,
            Statement=[
                awacs.aws.Statement(
                    Effect=awacs.aws.Allow,
                    Action=[
                        awacs.aws.Action("cloudformation", "*"),
                        awacs.aws.Action("ec2", "*"),
                        awacs.aws.Action("route53", "*"),
                        awacs.aws.Action("iam", "*"),
                        awacs.aws.Action("elasticloadbalancing", "*"),
                        awacs.aws.Action("s3", "*"),
                        awacs.aws.Action("autoscaling", "*"),
                        awacs.aws.Action("apigateway", "*"),
                        awacs.aws.Action("cloudwatch", "*"),
                        awacs.aws.Action("cloudfront", "*"),
                        awacs.aws.Action("rds", "*"),
                        awacs.aws.Action("dynamodb", "*"),
                        awacs.aws.Action("lambda", "*"),
                        awacs.aws.Action("sqs", "*"),
                        awacs.aws.Action("events", "*"),
                        awacs.ecr.GetDownloadUrlForLayer,
                        awacs.ecr.BatchGetImage,
                        awacs.ecr.BatchCheckLayerAvailability,
                        awacs.iam.PassRole,
                    ],
                    Resource=["*"]
                ),
                awacs.aws.Statement(
                    Effect=awacs.aws.Allow,
                    Action=[
                        awacs.logs.CreateLogGroup,
                        awacs.logs.CreateLogStream,
                        awacs.logs.PutLogEvents,
                    ],
                    # TODO: restrict more accurately
                    Resource=["*"]
                )
            ]
        )
    )
