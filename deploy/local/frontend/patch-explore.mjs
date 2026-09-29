import { readFileSync, writeFileSync } from 'node:fs';

// Apply only the shared Explore changes to the deployed release, not the
// unrelated redesign code in the development checkout. Fail on version drift.
const file = 'app/javascript/mastodon/features/explore/index.tsx';
let source = readFileSync(file, 'utf8');
for (const [anchor, replacement] of [
  ["import { NavLink, Switch, Route } from 'react-router-dom';", "import { NavLink, Switch, Route, useLocation } from 'react-router-dom';"],
  ["  const logoRequired = useBreakpoint('full');", "  const logoRequired = useBreakpoint('full');\n  const { pathname } = useLocation();"],
  ["import Links from './links';", "import Links from './links';\nimport Live from './live';"],
  ["        title={intl.formatMessage(messages.title)}", "        title={<span className='sr-only'>{intl.formatMessage(messages.title)}</span>}"],
  ["      <div className='account__section-headline'>", `      <div className='account__section-headline'>
        <NavLink exact to='/explore/live' className={pathname === '/' ? 'active' : undefined}>
          <FormattedMessage tagName='div' id='explore.live' defaultMessage='Live' />
        </NavLink>
`],
  ['      <Switch>', `      <Switch>
        <Route exact path={['/', '/explore/live']}>
          <Live multiColumn={multiColumn} />
        </Route>`],
]) {
  if (source.split(anchor).length !== 2) throw new Error(`Unexpected release source: ${anchor}`);
  source = source.replace(anchor, replacement);
}
writeFileSync(file, source);

const routerFile = 'app/javascript/mastodon/features/ui/index.jsx';
const router = readFileSync(routerFile, 'utf8');
const rootRoute = "            <Redirect from='/' to={{pathname: rootRedirect, state: {...this.props.location.state, focusTarget: false}}} exact />";
if (router.split(rootRoute).length !== 2) throw new Error('Unexpected release root route');
writeFileSync(routerFile, router.replace(rootRoute, `            {signedIn && forceOnboarding ? (
${rootRoute}
            ) : (
              <WrappedRoute path='/' exact component={Explore} content={children} />
            )}`));

const navigationFile = 'app/javascript/mastodon/features/navigation_panel/index.tsx';
let navigation = readFileSync(navigationFile, 'utf8');
const start = navigation.indexOf('        {trendsEnabled && (\n');
const end = navigation.indexOf('        {signedIn && (\n', start);
if (start < 0 || end < 0) throw new Error('Unexpected release navigation links');
navigation = navigation.slice(0, start) + navigation.slice(end);
for (const [anchor, replacement] of [
  ["import PublicIcon from '@/material-icons/400-24px/public.svg?react';\n", ''],
  ["import TrendingUpIcon from '@/material-icons/400-24px/trending_up.svg?react';\n", ''],
  ["import {\n  localLiveFeedAccess,\n  remoteLiveFeedAccess,\n  trendsEnabled,\n  me,\n} from 'mastodon/initial_state';", "import { me } from 'mastodon/initial_state';"],
  ["import { canViewFeed } from 'mastodon/permissions';\n", ''],
  ["  explore: { id: 'explore.title', defaultMessage: 'Trending' },\n  firehose: { id: 'column.firehose', defaultMessage: 'Live feeds' },\n  firehose_singular: {\n    id: 'column.firehose_singular',\n    defaultMessage: 'Live feed',\n  },\n", ''],
  ["const isFirehoseActive = (\n  match: unknown,\n  { pathname }: { pathname: string },\n) => {\n  return !!match || pathname.startsWith('/public');\n};\n\n", ''],
  ['const { signedIn, permissions, disabledAccountId } = useIdentity();', 'const { signedIn, disabledAccountId } = useIdentity();'],
]) {
  if (navigation.split(anchor).length !== 2) throw new Error(`Unexpected release navigation source: ${anchor}`);
  navigation = navigation.replace(anchor, replacement);
}
writeFileSync(navigationFile, navigation);

const trendsFile = 'app/javascript/mastodon/features/navigation_panel/components/trends.tsx';
let trends = readFileSync(trendsFile, 'utf8');
for (const [anchor, replacement] of [
  ["import { Link } from 'react-router-dom';\n\n", ''],
  ["          <Link to={'/explore/tags'}>\n            <FormattedMessage\n              id='trends.trending_now'\n              defaultMessage='Trending now'\n            />\n          </Link>", "          <FormattedMessage\n            id='trends.trending_now'\n            defaultMessage='Trending now'\n          />"],
]) {
  if (trends.split(anchor).length !== 2) throw new Error(`Unexpected release trends source: ${anchor}`);
  trends = trends.replace(anchor, replacement);
}
writeFileSync(trendsFile, trends);

const detailFile = 'app/javascript/mastodon/features/status/index.jsx';
let detail = readFileSync(detailFile, 'utf8');
for (const [anchor, replacement] of [
  ["import { RefreshController } from './components/refresh_controller';", "import { RefreshController } from './components/refresh_controller';\nimport ThreadedReplies from './threaded_replies';"],
  ['      descendants = <>{this.renderChildren(descendantsIds)}</>;', "      descendants = <ThreadedReplies key={status.get('id')} ids={descendantsIds} rootId={status.get('id')} newlyAddedIds={this.state.newRepliesIds} />;"],
]) {
  if (detail.split(anchor).length !== 2) throw new Error(`Unexpected release status detail: ${anchor}`);
  detail = detail.replace(anchor, replacement);
}
writeFileSync(detailFile, detail);

const composeFile = 'app/javascript/mastodon/reducers/compose.js';
let compose = readFileSync(composeFile, 'utf8');
for (const [anchor, replacement] of [
  ["import { Map as ImmutableMap, List as ImmutableList, OrderedSet as ImmutableOrderedSet, fromJS } from 'immutable';", "import { Map as ImmutableMap, List as ImmutableList, fromJS } from 'immutable';"],
  ["function statusToTextMentions(state, status) {\n  let set = ImmutableOrderedSet([]);\n\n  if (status.getIn(['account', 'id']) !== me) {\n    set = set.add(`@${status.getIn(['account', 'acct'])} `);\n  }\n\n  return set.union(status.get('mentions').filterNot(mention => mention.get('id') === me).map(mention => `@${mention.get('acct')} `)).join('');\n}", "function statusToTextMentions(status) {\n  return status.getIn(['account', 'id']) === me ? '' : `@${status.getIn(['account', 'acct'])} `;\n}"],
  ["statusToTextMentions(state, action.status)", "statusToTextMentions(action.status)"],
]) {
  if (compose.split(anchor).length !== 2) throw new Error(`Unexpected release compose source: ${anchor}`);
  compose = compose.replace(anchor, replacement);
}
writeFileSync(composeFile, compose);

for (const path of [
  'app/javascript/mastodon/components/status_action_bar/index.jsx',
  'app/javascript/mastodon/components/status/action_bar.tsx',
  'app/javascript/mastodon/features/status/components/action_bar.jsx',
]) {
  let actionBar = readFileSync(path, 'utf8');
  const replyImport = "import ReplyIcon from '@/material-icons/400-24px/reply.svg?react';";
  const replyAllImport = "import ReplyAllIcon from '@/material-icons/400-24px/reply_all.svg?react';\n";
  if (actionBar.split(replyImport).length !== 2 || actionBar.split(replyAllImport).length !== 2) {
    throw new Error(`Unexpected release reply icons: ${path}`);
  }
  actionBar = actionBar.replace(replyImport, "import ReplyIcon from '@/material-icons/400-24px/comment.svg?react';");
  actionBar = actionBar.replace(replyAllImport, '').replaceAll('ReplyAllIcon', 'ReplyIcon');
  writeFileSync(path, actionBar);
}

for (const [locale, label] of [['en', 'Live'], ['zh-CN', '实况']]) {
  const path = `app/javascript/mastodon/locales/${locale}.json`;
  const messages = JSON.parse(readFileSync(path, 'utf8'));
  messages['explore.live'] = label;
  messages['local.thread.view_replies'] = locale === 'zh-CN' ? '查看 {count} 条回复' : 'View {count} replies';
  messages['local.thread.more_replies'] = locale === 'zh-CN' ? '再查看 {count} 条回复' : 'View {count} more replies';
  messages['local.thread.more_comments'] = locale === 'zh-CN' ? '加载更多评论' : 'Load more comments';
  messages['local.thread.hide_replies'] = locale === 'zh-CN' ? '收起回复' : 'Hide replies';
  writeFileSync(path, `${JSON.stringify(messages, null, 2)}\n`);
}
