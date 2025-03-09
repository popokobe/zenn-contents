---
title: "[自動更新]AWSがIPアドレスを公開しているサービス一覧"
emoji: "📰"
type: "tech" # tech: 技術記事 / idea: アイデア
topics: ["aws", "vpc", "network", "ip"]
published: true
---

## はじめに
[AWS IP アドレスの範囲](https://docs.aws.amazon.com/ja_jp/vpc/latest/userguide/aws-ip-ranges.html)の通り、[ip-ranges.json](https://ip-ranges.amazonaws.com/ip-ranges.json)でAWSのサービスで使用されるIPアドレスの範囲が公開されています。

運用負荷逓減のため、DNS名や[AWSマネージドプレフィックスリスト](https://docs.aws.amazon.com/ja_jp/vpc/latest/userguide/working-with-aws-managed-prefix-lists.html#available-aws-managed-prefix-lists)でトラフィック制御は行われるべきです。

しかし、以下のようにIPアドレスレベルでトラフィック制御を行わざるを得ない場合もあるかと思います。
- オンプレミス環境のファイアウォールでAWSサービスからのみ通信を許可したい
- コンプライアンス要件でネットワークACLの利用が義務付けられている

そこで今回は具体的に何のAWSサービスがIPアドレスを公開しているかを調べてみました。

## AWSがIPアドレスを公開しているサービス一覧
最新の情報を取得できるようGitHub Actionsでworkflowを組んでいます。
毎日0時(JST)に[ip-ranges.json](https://ip-ranges.amazonaws.com/ip-ranges.json)から`service`のみを抽出し、zenn-cli経由でAWSサービス一覧が更新されています。

**最終更新日時：<!-- LAST_CHECK_DATE_START --> 2025/03/10 00:08 <!-- LAST_CHECK_DATE_END -->**
<!-- AWS_SERVICES_LIST_START -->
```
AMAZON
AMAZON_APPFLOW
AMAZON_CONNECT
API_GATEWAY
CHIME_MEETINGS
CHIME_VOICECONNECTOR
CLOUD9
CLOUDFRONT
CLOUDFRONT_ORIGIN_FACING
CODEBUILD
DYNAMODB
EBS
EC2
EC2_INSTANCE_CONNECT
GLOBALACCELERATOR
IVS_REALTIME
KINESIS_VIDEO_STREAMS
MEDIA_PACKAGE_V2
ROUTE53
ROUTE53_HEALTHCHECKS
ROUTE53_HEALTHCHECKS_PUBLISHING
ROUTE53_RESOLVER
S3
WORKSPACES_GATEWAYS
```
<!-- AWS_SERVICES_LIST_END -->

## 一部のサービスはAMAZONにIPアドレスが包含されている
[Classmethodさんの記事](https://dev.classmethod.jp/articles/tsnote-aws-how-do-i-find-the-ip-address-range-for-a-specific-aws-service/)によれば、一部のサービスは`AMAZON`という大きな括りでIPアドレスが公開されている場合があるようです。

この場合、特定のサービスからのトラフフィックのみを許可するといった細かい制御ができません。
将来的にそのサービス単体でIPアドレス一覧が公開されるように祈りましょう。

## 補足 : AWS公式のSNSトピック
[AWSのIPアドレス範囲の通知](https://docs.aws.amazon.com/ja_jp/vpc/latest/userguide/subscribe-notifications.html)によれば、AWSが公式で`AmazonIpSpaceChanged`というSNSトピックを用意しているようです。

SNSサブスクライバーに運用担当者のメールアドレス等を設定し、変更を通知するといったワークフローが組めそうですね。
Lambdaをサブスクライバーに設定し、自動的にネットワークACLを変更するワークフローも面白そうです。

## 参考記事
- [AWS IP アドレスの範囲](https://docs.aws.amazon.com/ja_jp/vpc/latest/userguide/aws-ip-ranges.html)
- [特定の AWS サービスの IP アドレス範囲を調べる方法を教えてください](https://dev.classmethod.jp/articles/tsnote-aws-how-do-i-find-the-ip-address-range-for-a-specific-aws-service/)