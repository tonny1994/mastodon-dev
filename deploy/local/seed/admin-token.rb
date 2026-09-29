require 'json'
owner = User.find_by!(email: 'admin@mastodon.test.com')
app = Doorkeeper::Application.find_by!(name: '本机社区功能测试')
token = Doorkeeper::AccessToken.create!(application: app, resource_owner_id: owner.id, scopes: 'read write follow push')
puts JSON.generate(token: token.token, id: owner.account_id.to_s)
