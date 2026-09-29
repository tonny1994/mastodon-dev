require 'json'
owner = User.find_by!(email: 'admin@mastodon.test.com')
invite = Invite.create!(user: owner, max_uses: 1000, expires_at: 2.days.from_now, comment: 'Local 1000-user fixture run', autofollow: false)
puts JSON.generate(invite_code: invite.code, invite_id: invite.id, admin_account_id: owner.account_id.to_s)
