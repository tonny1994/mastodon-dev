require 'json'
input = JSON.parse(File.read('/tmp/local-fixture-audit-input.json'))
ids = input.fetch('account_ids').map(&:to_i)
accounts = Account.where(id: ids)
users = User.where(account_id: ids)
statuses = Status.where(account_id: ids).reorder(nil)
media = MediaAttachment.where(account_id: ids).reorder(nil)
threads = input.fetch('roots').map do |id|
  root = Status.find(id)
  descendants = Status.where(conversation_id: root.conversation_id).where.not(id: root.id).where(reblog_of_id: nil)
  parents = descendants.pluck(:id, :in_reply_to_id).to_h
  depths = parents.keys.map do |child|
    depth = 0
    cursor = child
    while cursor && cursor != root.id && depth < 100
      cursor = parents[cursor]
      depth += 1
    end
    depth
  end
  { id: root.id.to_s, url: "https://mastodon.test.com/@#{root.account.username}/#{root.id}", direct_comments: descendants.where(in_reply_to_id: root.id).count,
    nested_replies: descendants.where.not(in_reply_to_id: root.id).count, authors: descendants.distinct.count(:account_id), max_depth: depths.max }
end
puts JSON.pretty_generate({
  accounts: accounts.count, confirmed: users.where.not(confirmed_at: nil).count, approved: users.where(approved: true).count,
  avatars: accounts.where.not(avatar_file_name: nil).count, headers: accounts.where.not(header_file_name: nil).count,
  distinct_display_names: accounts.distinct.count(:display_name),
  posts_without_reblogs: statuses.where(reblog_of_id: nil, in_reply_to_id: nil).count,
  replies: statuses.where(reblog_of_id: nil).where.not(in_reply_to_id: nil).count,
  visibility: statuses.where(reblog_of_id: nil).group(:visibility).count,
  languages: statuses.where(reblog_of_id: nil).group(:language).count,
  media_types: media.where.not(status_id: nil).group(:type).count,
  failed_attached_media: media.where(processing: :failed).where.not(status_id: nil).count,
  failed_unattached_media: media.where(processing: :failed, status_id: nil).count,
  polls: Poll.where(account_id: ids).count,
  expired_polls: Poll.where(account_id: ids).where('expires_at < ?', Time.now.utc).count,
  poll_votes: PollVote.where(account_id: ids).count,
  favourites: Favourite.where(account_id: ids).count,
  bookmarks: Bookmark.where(account_id: ids).count,
  follows: Follow.where(account_id: ids).count,
  reblogs: statuses.where.not(reblog_of_id: nil).count,
  edited_statuses: StatusEdit.where(account_id: ids).distinct.count(:status_id),
  sensitive_statuses: statuses.where(sensitive: true).count,
  cw_statuses: statuses.where.not(spoiler_text: '').count,
  lists: List.where(account_id: ids).count,
  filters: CustomFilter.where(account_id: ids).count,
  threads: threads
})
