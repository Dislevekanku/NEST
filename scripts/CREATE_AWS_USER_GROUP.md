# How to Create AWS IAM User Group with EC2 Permissions

## Step 1: Access IAM Console

1. Log into the **AWS Console** with an admin account
2. Search for **IAM** in the top search bar
3. Click on **IAM** service

## Step 2: Create User Group

1. In the left sidebar, click **User groups**
2. Click **Create group** button
3. Enter a group name: `nanda-deployment-group` (or any name you prefer)
4. Click **Next**

## Step 3: Attach Permissions Policy

You can either:

### Option A: Attach AWS Managed Policy (Easier)

1. In the **Permissions policies** section, click **Add permissions** → **Attach policies directly**
2. Search for and select: **AmazonEC2FullAccess**
3. Click **Next**
4. Review and click **Create group**

### Option B: Create Custom Policy (More Secure - Recommended)

1. In the **Permissions policies** section, click **Add permissions** → **Create policy**
2. Click the **JSON** tab
3. Paste this policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "EC2DeploymentPermissions",
            "Effect": "Allow",
            "Action": [
                "ec2:RunInstances",
                "ec2:DescribeInstances",
                "ec2:DescribeSecurityGroups",
                "ec2:CreateSecurityGroup",
                "ec2:AuthorizeSecurityGroupIngress",
                "ec2:RevokeSecurityGroupIngress",
                "ec2:DescribeKeyPairs",
                "ec2:CreateKeyPair",
                "ec2:DescribeImages",
                "ec2:DescribeTags",
                "ec2:CreateTags",
                "ec2:TerminateInstances",
                "ec2:StopInstances",
                "ec2:StartInstances",
                "sts:GetCallerIdentity"
            ],
            "Resource": "*"
        }
    ]
}
```

4. Click **Next**
5. Give the policy a name: `NANDADeploymentPolicy`
6. Click **Create policy**
7. Go back to creating the user group
8. Click **Refresh** next to permissions
9. Search for and select: **NANDADeploymentPolicy**
10. Click **Next**
11. Review and click **Create group**

## Step 4: Add User to Group

1. Click on the group you just created
2. Click the **Users** tab
3. Click **Add users**
4. Select the user: **Disleve_kanku** (or your username)
5. Click **Add users**

## Step 5: Verify Permissions

The user `Disleve_kanku` should now have EC2 deployment permissions.

### Test with AWS CLI

```powershell
aws sts get-caller-identity
aws ec2 describe-instances --region us-east-1 --max-items 1
```

If these commands work, the permissions are active.

---

## Alternative: Use AWS CLI (Command Line)

If you prefer using AWS CLI instead of the console:

### Create the Policy

```bash
cat > nanda-deployment-policy.json << 'EOF'
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "EC2DeploymentPermissions",
            "Effect": "Allow",
            "Action": [
                "ec2:RunInstances",
                "ec2:DescribeInstances",
                "ec2:DescribeSecurityGroups",
                "ec2:CreateSecurityGroup",
                "ec2:AuthorizeSecurityGroupIngress",
                "ec2:RevokeSecurityGroupIngress",
                "ec2:DescribeKeyPairs",
                "ec2:CreateKeyPair",
                "ec2:DescribeImages",
                "ec2:DescribeTags",
                "ec2:CreateTags",
                "ec2:TerminateInstances",
                "sts:GetCallerIdentity"
            ],
            "Resource": "*"
        }
    ]
}
EOF

aws iam create-policy \
    --policy-name NANDADeploymentPolicy \
    --policy-document file://nanda-deployment-policy.json
```

### Create the Group

```bash
aws iam create-group --group-name nanda-deployment-group
```

### Attach Policy to Group

```bash
# Get your AWS account ID first
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws iam attach-group-policy \
    --group-name nanda-deployment-group \
    --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/NANDADeploymentPolicy
```

### Add User to Group

```bash
aws iam add-user-to-group \
    --group-name nanda-deployment-group \
    --user-name Disleve_kanku
```

---

## Minimal Permissions (If Custom Policy Doesn't Work)

If you need the absolute minimum permissions for the deployment script to work:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:RunInstances",
                "ec2:DescribeSecurityGroups",
                "ec2:CreateSecurityGroup",
                "ec2:AuthorizeSecurityGroupIngress",
                "ec2:DescribeKeyPairs",
                "ec2:CreateKeyPair",
                "ec2:CreateTags"
            ],
            "Resource": "*"
        }
    ]
}
```

---

## Notes

- **Policy propagation**: IAM policy changes can take a few seconds to propagate. If permissions don't work immediately, wait 1-2 minutes and try again.

- **Resource restrictions**: The policy above uses `"Resource": "*"` which allows actions on all EC2 resources. For production, you may want to restrict this to specific resources.

- **Admin required**: You need admin/root access or an account with IAM permissions to create groups and attach policies.

---

## After Setting Up Permissions

Once the user is added to the group with permissions, try the deployment again:

```bash
cd NEST
bash scripts/deploy_finance_consumer_agents.sh \
  "YOUR_ANTHROPIC_API_KEY" \
  "http://registry.chat39.com:6900" \
  "us-east-1" \
  "t3.micro"
```
