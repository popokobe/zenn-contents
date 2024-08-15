---
title: "Dockerで鍵認証によるAnsibleとansible_specの実行環境を構築"
emoji: "🧬"
type: "tech" # tech: 技術記事 / idea: アイデア
topics: ["linux", "docker", "ansible", "ruby", "ansiblespec"]
published: true
---
## はじめに
### 概要
本記事では以下の手順でハンズオンを行います。
1. DockerでAnsibleのコントロールノード1台(Ubuntu)とターゲットホスト1台(Ubuntu)を構築
2. Ansibleでapache2のインストール及び起動
3. ansible_specでapche2のインストール確認

### 対象読者
- DockerでAnsibleの実行環境を作ってみたい人
- Dockerでrbenvを使ってRubyの実行環境を作ってみたい人
- ansible_specを使ってみたい人
- Ansibleで鍵認証によるplaybookの実行をしたい人

:::message
- 基本的なDocker, Linuxコマンド(vim, etc.)は使えるものとします。
- 今回は環境構築がメインスコープなので、Ansible, ansible_specの詳細な説明はしていません。
:::

## ansible_specとは
この記事にたどり着いているということは[Ansible](https://www.ansible.com/)についてはご存知かと思うので詳細は割愛し、簡単にansible_specについて触れておきます。

[ansible_spec](https://github.com/volanja/ansible_spec "Github")とは、Ansibleと非常に相性の良いruby製のテスト自動化ツールになります。

テスト自動化ツールとして有名なものに[Serverspec](https://serverspec.org/)があります。
ただ、Ansibleで環境構築をし、Serverspecでテストを書く場合、対象のホストはそれぞれのディレクトリで管理する必要があり、ディレクトリ構成が少し煩雑になります。

そこでansible_specを導入することで、Ansibleのconfigやinventoryをparseし、設定や対象ホストを二重で管理する必要がなくなります。

## 前提条件
### Docker実行環境
Docker 26.1.4
Docker Compose 2.27.1

### OS, パッケージバージョン情報
Ubuntu 24.04

Python 3.12.3
ansible-core 2.16.9

rbenv 1.3.0
Ruby 3.1.6
ansible_spec 0.3.2
:::message alert
2024年8月14日現在、ansible_specの[commits](https://github.com/volanja/ansible_spec/commits/master/)を見ると`3.1.3`までのテストしか追加されていないため、それ以降のRubyのバージョンをインストールした場合、ansible_specが正常に動かない可能性があります。
:::

## ハンズオン環境
https://github.com/popokobe/ubuntu-ansible/tree/hands-on
まずは上記リポジトリをgit, GitHub Desktop, Github CLI等でローカルのPCにcloneします。

また、本ハンズオンで実行するコマンドと実行結果は[README](https://github.com/popokobe/ubuntu-ansible/blob/hands-on/README.md)にも記載しているので、まとめて見たい方はそちらも合わせて見てみてください。


### 忙しい人向け
https://github.com/popokobe/ubuntu-ansible/tree/master
本ハンズオンで行う操作をすでに実行済みのコンテナを用意しています。
Ansibleのinventory, playbook、そしてspecファイルも準備済みです。

詳しい実行方法はリポジトリの[README](https://github.com/popokobe/ubuntu-ansible/blob/master/README.md)を参照してください。

## ディレクトリ構成
```
.
├── compose.yml
├── ubuntu-c
│   ├── Dockerfile
│   └── deploy_ssh_keys.sh
└── ubuntu-t1
    └── Dockerfile
```

## Dockerコンテナ
このセクションではAnsibleコントロールノードとターゲットノードのDockerfileの説明とcompose.ymlの説明をしています。

このセクションの内容を理解してからハンズオンにとりかかるのが理想ですが、不要な方は読み飛ばして[ハンズオン](#ハンズオン)のセクションまで飛んでください。

### Ansibleコントロールノード
#### Dockerfile
```Dockerfile:./ubuntu-c/Dockerfile
# ========================
# Build stage for rbenv and ruby installation
# ========================
FROM ubuntu:24.04 AS builder

# Install necessary packages for building Ruby
RUN apt update && \
    apt install -y --no-install-recommends \
    curl \
    git \
    autoconf \
    patch \
    build-essential \
    rustc \
    libssl-dev \
    libyaml-dev \
    libreadline6-dev \
    zlib1g-dev \
    libgmp-dev \
    libncurses5-dev \
    libffi-dev \
    libgdbm6 \
    libgdbm-dev \
    libdb-dev \
    uuid-dev \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Set environment variables for rbenv and Ruby version    
ENV RBENV_ROOT=/opt/rbenv
ENV RUBY_VERSION=3.1.6

# Install rbenv and ruby-build, and build the specified Ruby version
RUN git clone https://github.com/rbenv/rbenv.git ${RBENV_ROOT} && \
    git clone https://github.com/rbenv/ruby-build.git ${RBENV_ROOT}/plugins/ruby-build && \
    ${RBENV_ROOT}/bin/rbenv install ${RUBY_VERSION} && \
    ${RBENV_ROOT}/bin/rbenv global ${RUBY_VERSION}

# ========================
# Runtime stage with rbenv, ruby, and ansible included
# ========================
FROM ubuntu:24.04 AS final

# Install packages for gems and install Ansible
RUN apt update && \
    apt install -y --no-install-recommends \
    build-essential \
    make \
    gcc \
    vim \
    curl \
    git \
    software-properties-common && \
    apt-add-repository --yes --update ppa:ansible/ansible && \
    apt install -y ansible && \
    rm -rf /var/lib/apt/lists/*

# Copy rbenv and the built Ruby version from the builder stage
COPY --from=builder /opt/rbenv /opt/rbenv

ENV RBENV_ROOT=/opt/rbenv
ENV PATH=${RBENV_ROOT}/bin:${RBENV_ROOT}/shims:$PATH

# Script for deploying ssh key to the target host
COPY deploy_ssh_keys.sh /root/deploy_ssh_keys.sh
RUN chmod +x /root/deploy_ssh_keys.sh

CMD ["/root/deploy_ssh_keys.sh"]

WORKDIR /etc/ansible
```
Ubuntuを実行環境としています。

なるべく軽量なdockerイメージにするためにマルチステージビルドを行い、rubyのビルドにしか使わないパッケージはプロダクションステージには含めていません。

**ビルドステージ**
1. rbenvのpluginとして動作させている[ruby-build](https://github.com/rbenv/ruby-build/wiki)のwikiを参考にrubyをビルドするために必要なパッケージをインストール
2. rbenv, ruby-buildをインストール
3. 特定のバージョンのrubyをインストールし、globalにセット

**プロダクションステージ**
1. [Ansibleの公式ドキュメント](https://docs.ansible.com/ansible/2.9_ja/installation_guide/intro_installation.html#ubuntu-ansible)を参考にAnsibleをインストール
2. ビルドステージからrubyの実行環境のみをコピー
3. 鍵認証でターゲットホストへ接続するためのセットアップスクリプトを配置

:::message
後述のansible_specをbundle installするときにmake, gcc等が必要なので、apt installしています。
:::

#### 公開鍵配置用スクリプト
```sh:./ubuntu-c/deploy_ssh_keys.sh
#!/bin/bash

# Generate ssh key
ssh-keygen -t ed25519 -f /root/.ssh/id_ed25519 -q -C "" -N ""

# Copy public ssh key to the target host
sshpass -p "password" ssh-copy-id -i /root/.ssh/id_ed25519.pub -o StrictHostKeyChecking=no root@ubuntu-t1

# Connect to target host, disable ssh connection with password authentication, and restart sshd
# "service restart ssh" will cause the container to crash, running "kill -HUP" command.
ssh root@ubuntu-t1 -p 22  << 'EOF'
sed -i 's/^PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
kill -HUP $(pgrep -x sshd)
EOF

# Avoid container termination
tail -f /dev/null

```
Ansibleコントロールノード上でSSHキーペアを作成した後、公開鍵をターゲットノードへsshpass, ssh-copy-idを使用して送信します。

その後、パスワード認証によるSSH接続を無効化し、SSHデーモンに対してHUPシグナルを送り設定反映を行います。
:::details service restart sshで設定反映をしていない理由
後述の`./ubuntu-t1/Dockerfile`の末尾で`CMD ["/usr/sbin/sshd", "-D"]`を指定しており、コンテナ起動と同時にでSSHデーモンも起動するようにしています。
DockerではCMDで実行したコマンドがPID 1として実行されます。
PID 1で実行されているプロセスがコンテナ全体のライフサイクルを管理しているため、それを終了(再起動=終了→起動)させることでコンテナ自体が終了してしまいます。

したがって、`kill -HUP`コマンドを用いることで、デーモンを再起動させることなく設定を再読み込みしています。
:::

### Ansibleターゲットノード
#### Dockerfile
```Dockerfile:./ubuntu-t1/Dockerfile
FROM ubuntu:24.04

# Install package for ssh server to connect from ansible control node
RUN apt update && \
    apt install -y openssh-server sudo && \
    rm -rf /var/lib/apt/lists/*

# Make a directory for sshd (apparently the server will not start without this directory)
# Password authentication is set to yes temporarily, but after copying the public key from the ansible control node, 
# it is to be disabled
RUN mkdir /var/run/sshd && \
    echo 'root:password' | chpasswd && \
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

# Start ssh server
CMD ["/usr/sbin/sshd", "-D"]
```
1. SSHサーバ用にopenssh-server, ansible_specで接続する用にsudoをインストール
2. rootユーザのパスワードを設定
3. rootでのSSH接続及びパスワード認証を許可
4. SSHサーバの起動

前述の`deploy_ssh_keys.sh`で公開鍵を配置するために、コンテナ作成時はパスワード認証を有効化しています。

### サービス定義
```yaml:./compose.yml
services:
  ubuntu-c:
    container_name: ubuntu-c
    hostname: ubuntu-c
    build:
      context: ./ubuntu-c
      target: final
    depends_on:
    - ubuntu-t1
    tty: true

  ubuntu-t1:
    container_name: ubuntu-t1
    hostname: ubuntu-t1
    build: ./ubuntu-t1
    ports:
    - 2222:22
    - 8080:80
    tty: true
```
#### service: ubuntu-c
`build`のtargetとして、`./ubuntu-c/Dockerfile`のプロダクションステージを明示的に指定しています。

`depends_on`でubuntu-cをubuntu-t1に依存する指定をし、ubuntu-t1→ubuntu-cの順番でコンテナが起動するようにしています。
これは`deploy_ssh_keys.sh`で公開鍵をubuntu-t1へ配置するとき、ubuntu-t1が起動していないとできないためです。

#### service: ubuntu-t1
`ports`でSSH(22)とHTTP(80)のポートを開けています。
ホスト側の2222番ポートをSSHに、8080番ポートをHTTPに割り当てています。

## ハンズオン
### ハンズオン終了後のAnsibleコントロールノードのディレクトリ構成
```
/etc/ansible
├── Gemfile
├── Gemfile.lock
├── Rakefile
├── ansible.cfg
├── hosts
├── roles
│   └── apache2
│       ├── spec
│       │   └── apache2_spec.rb
│       └── tasks
│           └── main.yaml
├── site.yml
└── spec
    └── spec_helper.rb
```
事前にイメージをしておいたほうが進めやすいかと思うので、ハンズオン終了後のディレクトリ構成を置いておきます。

### コンテナのビルド・起動
それでは早速ハンズオンをしていきましょう。
```sh
docker compose up -d --build
```
`compose.yml`があるディレクトリで以上のコマンドを実行し、コンテナのビルドと起動を行います。
`ubuntu-c`のビルドに時間がかかるので、しばらくお待ちください。
<br>
```sh
docker compose exec ubuntu-c bash
```
コンテナが立ち上がったら、Ansibleコントロールノードへ接続します。

### パスワード認証でSSHできないことの確認
```
root@ubuntu-c:/etc/ansible# ssh root@ubuntu-t1 -o PreferredAuthentications=password
root@ubuntu-t1: Permission denied (publickey).

root@ubuntu-c:/etc/ansible# ssh root@ubuntu-t1
Welcome to Ubuntu 24.04 LTS (GNU/Linux 6.6.31-linuxkit aarch64)

 * Documentation:  https://help.ubuntu.com
 * Management:     https://landscape.canonical.com
 * Support:        https://ubuntu.com/pro

This system has been minimized by removing packages and content that are
not required on a system that users do not log into.

To restore this content, you can run the 'unminimize' command.
Last login: Sat Aug 10 14:41:38 2024 from 172.18.0.3
root@ubuntu-t1:~#
```
`ssh root@ubuntu-t1 -o PreferredAuthentications=password`で明示的にパスワード認証でSSHしようとすると、ubuntu-t1から`root@ubuntu-t1: Permission denied (publickey).`で怒られるかと思います。

これは[公開鍵配置用スクリプト](#公開鍵配置用スクリプト)でパスワード認証によるSSH接続を無効化しているためです。

`ssh root@ubuntu-t1`で接続を試みるとパスワード入力をプロンプトされることなく、鍵認証でubuntu-t1へ接続できます。

### Ansibleセットアップ
#### hostsの作成
```
root@ubuntu-c:/etc/ansible# vim hosts
```
まずは`/etc/ansible`配下にAnsibleのインベントリファイルを作成します。

```ini:hosts
[webservers]
ubuntu-t1 ansible_ssh_private_key_file=/root/.ssh/id_ed25519
```
鍵認証をするために、`ansible_ssh_private_key_file`で秘密鍵のパスを指定しています。

#### Ansible疎通確認
```
root@ubuntu-c:/etc/ansible# ansible -m ping webservers
ubuntu-t1 | SUCCESS => {
    "ansible_facts": {
        "discovered_interpreter_python": "/usr/bin/python3"
    },
    "changed": false,
    "ping": "pong"
}
```
Ansibleのping moduleで疎通確認をし、pongと返ってくれば成功です。

#### rolesの作成
今回は例としてapache2をインストールし、webサーバを立ち上げたいと思います。

```
root@ubuntu-c:/etc/ansible# cd roles
root@ubuntu-c:/etc/ansible/roles# mkdir -p apache2/tasks   
root@ubuntu-c:/etc/ansible/roles# cd apache2/tasks
root@ubuntu-c:/etc/ansible/roles/apache2/tasks# vim main.yml
```

```yaml:/etc/ansible/roles/apache2/tasks/main.yml
- name: Install apache package
  apt:
    name: apache2
    state: present

- name: Start apeche2 server
  service:
    name: apache2
    state: started
```
apache2をインストールし立ち上げるという簡単なroleを作成します。

#### playbookの作成
```
root@ubuntu-c:/etc/ansible# cd /etc/ansible
root@ubuntu-c:/etc/ansible# vim site.yml
```
```yaml:/etc/ansible/site.yml
- name: Deploy apache server
  gather_facts: no
  hosts: webservers
  roles:
  - apache2
```
先ほど作成したroleを用いたplaybookを作成します。
<br>

ここで、Ansible Playbookを実行してみましょうと行きたいところですが、念の為ターゲットノードにapache2がインストールされていないことを確認してみます。
```
root@ubuntu-c:/etc/ansible# ssh ubuntu-t1
Welcome to Ubuntu 24.04 LTS (GNU/Linux 6.6.31-linuxkit aarch64)

 * Documentation:  https://help.ubuntu.com
 * Management:     https://landscape.canonical.com
 * Support:        https://ubuntu.com/pro

This system has been minimized by removing packages and content that are
not required on a system that users do not log into.

To restore this content, you can run the 'unminimize' command.
Last login: Sat Aug 10 14:57:28 2024 from 172.18.0.3
root@ubuntu-t1:~# apt list --installed | grep apache2
root@ubuntu-t1:~# exit
logout
Connection to ubuntu-t1 closed.
```
SSHでubuntu-t1へ接続します。
`apt list --installed | grep apache2`でインストールされているパッケージを一覧表示し、その中に"apache2"と名前がついたものがないことを確認します。

#### playbookの実行
```
root@ubuntu-c:/etc/ansible# ansible-playbook site.yml

PLAY [Deploy apache server] **********************************************************************************************************************

TASK [apache2 : Install apache package] **********************************************************************************************************
changed: [ubuntu-t1]

TASK [apache2 : Start apeche2 server] ************************************************************************************************************
changed: [ubuntu-t1]

PLAY RECAP ***************************************************************************************************************************************
ubuntu-t1                  : ok=2    changed=2    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0   

```
それでは`ansible-playbook`コマンドでplaybookを実行します。少し時間がかかるので待ちましょう。
`ok=2    changed=2`という表記があれば、playbookが成功したといえます。
<br>
ubuntu-t1へ接続して、apache2がインストールされていることを確認します。
```
root@ubuntu-c:/etc/ansible# ssh ubuntu-t1
Welcome to Ubuntu 24.04 LTS (GNU/Linux 6.6.31-linuxkit aarch64)

 * Documentation:  https://help.ubuntu.com
 * Management:     https://landscape.canonical.com
 * Support:        https://ubuntu.com/pro

This system has been minimized by removing packages and content that are
not required on a system that users do not log into.

To restore this content, you can run the 'unminimize' command.
Last login: Sat Aug 10 14:57:28 2024 from 172.18.0.3
root@ubuntu-t1:~# apt list --installed | grep apache2

WARNING: apt does not have a stable CLI interface. Use with caution in scripts.

apache2-bin/noble-updates,noble-security,now 2.4.58-1ubuntu8.4 arm64 [installed,automatic]
apache2-data/noble-updates,noble-security,now 2.4.58-1ubuntu8.4 all [installed,automatic]
apache2-utils/noble-updates,noble-security,now 2.4.58-1ubuntu8.4 arm64 [installed,automatic]
apache2/noble-updates,noble-security,now 2.4.58-1ubuntu8.4 arm64 [installed]
root@ubuntu-t1:~# exit
logout
Connection to ubuntu-t1 closed.
```
apache2関連のパッケージがインストールされていることが確認できます。

<br>
これでwebserverの起動まで完了したので、ブラウザで [http://localhost:8080](http://localhost:8080) を開いてみます。
![](/images/ubuntu-ansible/apache2-default-page.png)
上記のようなApache2 Default Pageが表示されれば成功です。

### ansible_specセットアップ
次にansible_specでテストの実行環境を作っていきます。

#### Rubyインストール確認
```
root@ubuntu-c:/etc/ansible# ruby --version
ruby 3.1.6p260 (2024-05-29 revision a777087be6) [aarch64-linux]
```
ansible_specはruby製のツールのため、まずはrubyがインストールされていることを確認します。
#### Gemfileを作成し、bundle install
```
root@ubuntu-c:/etc/ansible# vim Gemfile
```
```:/etc/ansible/Gemfile
source 'https://rubygems.org'

gem 'ansible_spec', '0.3.2'

# === Gem for public key authentication with ansible_spec ===
gem 'ed25519', '1.3.0'
gem 'bcrypt_pbkdf', '1.1.1'
# ===========================================================
```
今回は依存関係の解決の簡単のためbundlerを使用します。
まずはプロジェクト直下にGemfileを記述します。

ansible_spec以外にもed25519, bcrypt_pbkdfをインストールしますが、これらはansible_specがEd25519で暗号化された鍵でターゲットノードへ接続する際に必要です。
<br>
```
root@ubuntu-c:/etc/ansible# bundle install
Don't run Bundler as root. Bundler can ask for sudo if it is needed, and installing your bundle as root will break this application for all
non-root users on this machine.
Fetching gem metadata from https://rubygems.org/.............
Resolving dependencies...
Fetching multi_json 1.15.0
.
.
.
Fetching ansible_spec 0.3.2
Installing ansible_spec 0.3.2
Bundle complete! 3 Gemfile dependencies, 39 gems now installed.
Use `bundle info [gemname]` to see where a bundled gem is installed.
root@ubuntu-c:/etc/ansible# ls
Gemfile  Gemfile.lock  ansible.cfg  hosts  roles  site.yml
```
Gemfileの内容をもとに`bundle install`をします。
プロジェクト配下にGemfile.lockが生成され、gemが使用可能になります。
#### ansiblespec-init
```
root@ubuntu-c:/etc/ansible# ansiblespec-init
                create  spec
                create  spec/spec_helper.rb
                create  Rakefile
                create  .ansiblespec
                create  .rspec
```
[ansible_spec](https://github.com/volanja/ansible_spec)公式のreadmeにしたがい、ansible_specの実行に必要なファイルを生成します。
#### テストコード作成
```
root@ubuntu-c:/etc/ansible# mkdir -p roles/apache2/spec
root@ubuntu-c:/etc/ansible# cd roles/apache2/spec
root@ubuntu-c:/etc/ansible/roles/apache2/spec# vim apache2_spec.rb
```
```ruby:/etc/ansible/roles/apache2/spec/apache2_spec.rb
require 'spec_helper'

describe package('apache2') do
  it { should be_installed }
end
```
ansible_specはデフォルトで`roles/[task名]/spec/*_spec.rb`を読み込みます。
`/etc/ansible/roles/apache2/spec/`配下に`apache2_spec.rb`を作成し、`apache2`がインストールされているか確認するテストコードを書きます。
#### テスト実行
```
root@ubuntu-c:/etc/ansible/roles/apache2/spec# cd /etc/ansible
root@ubuntu-c:/etc/ansible# rake -T
rake all                              # Run serverspec to all test
rake serverspec:Deploy apache server  # Run serverspec for Deploy apache server
```
`/etc/ansible`に移動し、実行されるテストを一覧表示します。
今回はapache2のインストールを確認するものしか書いていないため、`rake all`の他に`rake serverspec:Deploy apache server`しか表示されません。
<br>
```
root@ubuntu-c:/etc/ansible# rake all
Run serverspec for Deploy apache server to {"name"=>"ubuntu-t1 ansible_ssh_private_key_file=/root/.ssh/id_ed25519", "port"=>22, "connection"=>"ssh", "uri"=>"ubuntu-t1", "private_key"=>"/root/.ssh/id_ed25519"}
/opt/rbenv/versions/3.1.6/bin/ruby -I/opt/rbenv/versions/3.1.6/lib/ruby/gems/3.1.0/gems/rspec-support-3.13.1/lib:/opt/rbenv/versions/3.1.6/lib/ruby/gems/3.1.0/gems/rspec-core-3.13.0/lib /opt/rbenv/versions/3.1.6/lib/ruby/gems/3.1.0/gems/rspec-core-3.13.0/exe/rspec --pattern \{roles\}/\{apache2\}/spec/\*_spec.rb

Package "apache2"
/opt/rbenv/versions/3.1.6/lib/ruby/gems/3.1.0/gems/specinfra-2.90.1/lib/specinfra/backend/ssh.rb:82:in `create_ssh': Passing nil, or [nil] to Net::SSH.start is deprecated for keys: user
  is expected to be installed

Finished in 0.40293 seconds (files took 0.27431 seconds to load)
1 example, 0 failures
```
それでは、`rake all`でテストを実行します。
`ubuntu-t1`に対し、`"private_key"=>"/root/.ssh/id_ed25519"`で接続し、`1 example, 0 failures`と表示されます。

:::details もしテストが失敗したらどんな感じ？
ちなみに`ansible-playbook site.yml`を実行していない状態で、`rake all`を実行するともちろん以下のように失敗します。
```
root@ubuntu-c:/etc/ansible# rake all
Run serverspec for Deploy apache server to {"name"=>"ubuntu-t1 ansible_ssh_private_key_file=/root/.ssh/id_ed25519", "port"=>22, "connection"=>"ssh", "uri"=>"ubuntu-t1", "private_key"=>"/root/.ssh/id_ed25519"}
/opt/rbenv/versions/3.1.6/bin/ruby -I/opt/rbenv/versions/3.1.6/lib/ruby/gems/3.1.0/gems/rspec-support-3.13.1/lib:/opt/rbenv/versions/3.1.6/lib/ruby/gems/3.1.0/gems/rspec-core-3.13.0/lib /opt/rbenv/versions/3.1.6/lib/ruby/gems/3.1.0/gems/rspec-core-3.13.0/exe/rspec --pattern \{roles\}/\{apache2\}/spec/\*_spec.rb

Package "apache2"
/opt/rbenv/versions/3.1.6/lib/ruby/gems/3.1.0/gems/specinfra-2.90.1/lib/specinfra/backend/ssh.rb:82:in `create_ssh': Passing nil, or [nil] to Net::SSH.start is deprecated for keys: user
  is expected to be installed (FAILED - 1)

Failures:

  1) Package "apache2" is expected to be installed
     On host `ubuntu-t1'
     Failure/Error: it { should be_installed }
       expected Package "apache2" to be installed
       sudo -p 'Password: ' /bin/sh -c dpkg-query\ -f\ \'\$\{Status\}\'\ -W\ apache2\ \|\ grep\ -E\ \'\^\(install\|hold\)\ ok\ installed\$\'
       
     # ./roles/apache2/spec/apache2_spec.rb:4:in `block (2 levels) in <top (required)>'

Finished in 0.88866 seconds (files took 0.34924 seconds to load)
1 example, 1 failure

Failed examples:

rspec ./roles/apache2/spec/apache2_spec.rb:4 # Package "apache2" is expected to be installed

/opt/rbenv/versions/3.1.6/bin/ruby -I/opt/rbenv/versions/3.1.6/lib/ruby/gems/3.1.0/gems/rspec-support-3.13.1/lib:/opt/rbenv/versions/3.1.6/lib/ruby/gems/3.1.0/gems/rspec-core-3.13.0/lib /opt/rbenv/versions/3.1.6/lib/ruby/gems/3.1.0/gems/rspec-core-3.13.0/exe/rspec --pattern \{roles\}/\{apache2\}/spec/\*_spec.rb failed
```
:::

## 改善点
### Volumeの永続化ができていない
Volumeの永続化ができておらず、ハンズオン終了後にコンテナを落とすとデータが消失してしまいます。

```diff yml:comopse.yml
-     volumes:
-     - ./ubuntu-c/ansible:/etc/ansible
```
もともとは`compose.yml`でvolumesの指定をしていました。
ただ、このような指定をするとansible_specがうまく`hosts`を解釈せず、テストを実行することができませんでした。

原因は以下の記事にもある通り、ホストOSののuser id, group idとAnsibleコントロールノードのUbuntuのuser id, group idが異なるからでした。
https://qiita.com/cheekykorkind/items/ba912b62d1f59ea1b41e

この問題を解消することで、コンテナを終了させたとしてもデータが永続化され、ハンズオンをしやすい環境にしたいです。

### deploy_ssh_keys.shを複数ホストに対応させたい
```sh:./ubuntu-c/deploy_ssh_keys.sh
#!/bin/bash

詳細は省略

# Copy public ssh key to the target host
sshpass -p "password" ssh-copy-id -i /root/.ssh/id_ed25519.pub -o StrictHostKeyChecking=no root@ubuntu-t1
```
`ssh-copy-id`で公開鍵を配布する先を`root@ubuntu-t1`としているので、`compose.yml`で複数ホスト立ち上げたときに全ホストに公開鍵を配布できないです。

`comose.yml`の`services`と連動して、公開鍵を配布するホストを追加できるようにしたいと考えています。


### Dockerイメージを軽量化したい
`ubuntu-c`のビルド後のイメージサイズは1.09GBと巨大です。
これではイメージを保存するストレージを圧迫してしまいますし、なにしろビルド時間が長くなり開発効率が落ちてしまいます。そのため、実務レベルで使う場合はさらなる軽量化が必要だと考えています。
:::message
もし更に軽量にできそうであればぜひコメント等でアドバイスいただければと思います！
:::

Dockerについてはまだまだ勉強中ですが、今回は`ubuntu-c`のDockerfileで以下の点を工夫し、なるべくイメージサイズを軽くしようと努力しています。

- マルチステージビルドの活用
- `apt install -y --no-install-recommends`で不要なパッケージはインストールしない
- `rm -rf /var/lib/apt/lists/*`でaptキャッシュを削除



## 最後に
ハンズオンはこちらで終了です。
いかがでしたでしょうか。

本記事がDockerでのAnsible, ansible_specの環境構築に困っていた方等の助けになっていたら嬉しいです。

これが初記事につき至らない点も多くあるかと思います。その際はコメント等でご指摘いただければと思います。

## 参考記事
**Docker関連**
- [Dockerfile のベストプラクティス](https://docs.docker.jp/engine/articles/dockerfile_best-practice.html)
- [軽量なDockerイメージを作るために意識すること](https://zenn.dev/tsucchiiinoko/articles/7c096f387e8251)
- [夏に向けて、体もコンテナイメージも減量（軽量化）させよう！](https://qiita.com/yokoo-an209/items/0297808af40c1a74928e)
- [Docker Composeのvolumes使用時に出会うpermission deniedに対応する一つの方法](https://qiita.com/cheekykorkind/items/ba912b62d1f59ea1b41e)

**Ansible関連**
- [Installing Ansible on specific operating systems — Ansible Community Documentation](https://docs.ansible.com/ansible/latest/installation_guide/installation_distros.html)

**ansible_spec関連**
- [Ansible とServerspec 使っててなんでansible_spec 使わんの？](https://qiita.com/katsuhisa__/items/15236253e72a8de74b00)

**rbenv, ruby関連**
- [[備忘録] Docker上の Ubuntu 18.04 に rbenv を導入する](https://qiita.com/robozushi10/items/1d338ae24bbc37c5a8ec)
- [bundle install時に--path vendor/bundleを付ける必要性は本当にあるのか、もう一度よく考えてみよう](https://qiita.com/jnchito/items/99b1dbea1767a5095d85)

**SSH関連**
- [ssh接続可能なDockerコンテナの作成方法](https://qiita.com/TK_Yudai/items/7a8ecc077e4401f35e5d)