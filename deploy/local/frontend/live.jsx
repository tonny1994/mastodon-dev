import PropTypes from 'prop-types';
import { useCallback, useEffect } from 'react';

import { FormattedMessage } from 'react-intl';

import { connectCommunityStream } from 'mastodon/actions/streaming';
import { expandCommunityTimeline } from 'mastodon/actions/timelines';
import { useIdentity } from 'mastodon/identity_context';
import { localLiveFeedAccess } from 'mastodon/initial_state';
import { canViewFeed } from 'mastodon/permissions';
import { useAppDispatch } from 'mastodon/store';

import StatusListContainer from '../ui/containers/status_list_container';

const Live = ({ multiColumn }) => {
  const dispatch = useAppDispatch();
  const { signedIn, permissions } = useIdentity();
  const canView = canViewFeed(signedIn, permissions, localLiveFeedAccess);

  useEffect(() => {
    let disconnect;

    if (canView) {
      dispatch(expandCommunityTimeline());
      if (signedIn) disconnect = dispatch(connectCommunityStream());
    }

    return () => disconnect?.();
  }, [dispatch, signedIn, canView]);

  const handleLoadMore = useCallback(
    maxId => dispatch(expandCommunityTimeline({ maxId })),
    [dispatch],
  );

  if (!canView) {
    return (
      <div className='empty-column-indicator'>
        <FormattedMessage id='empty_column.disabled_feed' defaultMessage='This feed has been disabled by your server administrators.' />
      </div>
    );
  }

  return (
    <StatusListContainer
      timelineId='community'
      onLoadMore={handleLoadMore}
      trackScroll
      scrollKey='explore-live'
      emptyMessage={<FormattedMessage id='empty_column.community' defaultMessage='The local timeline is empty. Write something publicly to get the ball rolling!' />}
      bindToDocument={!multiColumn}
    />
  );
};

Live.propTypes = {
  multiColumn: PropTypes.bool,
};

export default Live;
