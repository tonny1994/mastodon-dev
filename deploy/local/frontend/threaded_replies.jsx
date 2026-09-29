import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';

import PropTypes from 'prop-types';

import { FormattedMessage } from 'react-intl';

import { useSelector } from 'react-redux';

import { StatusQuoteManager } from 'mastodon/components/status_quoted';

import styles from './threaded_replies.module.scss';

const ReplyGroup = ({ id, replies, rootId, newlyAddedIds }) => {
  const [visibleCount, setVisibleCount] = useState(0);
  const repliesRef = useRef(null);
  const toggleRef = useRef(null);
  const anchorRef = useRef(null);
  const collapsingRef = useRef(false);
  const animationRef = useRef(null);
  const shown = replies.length <= 3 ? replies : replies.slice(0, visibleCount);
  const remaining = replies.length - shown.length;
  useEffect(() => () => {
    collapsingRef.current = false;
    animationRef.current?.cancel();
  }, []);
  const showFirst = useCallback(() => setVisibleCount(5), []);
  const showMore = useCallback(() => setVisibleCount(count => count + 10), []);
  const keepAnchor = useCallback(() => {
    const button = toggleRef.current;
    const anchor = anchorRef.current;
    if (button && anchor) anchor.scroller.scrollTop += button.getBoundingClientRect().top - anchor.top;
  }, []);
  useLayoutEffect(() => {
    if (visibleCount === 0 && anchorRef.current) {
      keepAnchor();
      anchorRef.current = null;
    }
  }, [visibleCount, keepAnchor]);
  const collapse = useCallback(() => {
    if (collapsingRef.current) return;
    const element = repliesRef.current;
    const button = toggleRef.current;
    if (button) {
      let scroller = button.parentElement;
      while (scroller && !(/auto|scroll/.test(getComputedStyle(scroller).overflowY) && scroller.scrollHeight > scroller.clientHeight)) {
        scroller = scroller.parentElement;
      }
      anchorRef.current = { top: button.getBoundingClientRect().top, scroller: scroller || document.scrollingElement };
    }
    if (!element?.animate || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setVisibleCount(0);
      return;
    }
    collapsingRef.current = true;
    const track = () => {
      keepAnchor();
      if (collapsingRef.current) requestAnimationFrame(track);
    };
    requestAnimationFrame(track);
    const animation = element.animate(
      [{ height: `${element.offsetHeight}px` }, { height: '0px' }],
      { duration: 300, easing: 'ease-in-out', fill: 'forwards' },
    );
    animationRef.current = animation;
    animation.onfinish = () => {
      collapsingRef.current = false;
      animationRef.current = null;
      setVisibleCount(0);
    };
  }, [keepAnchor]);

  return (
    <div className={styles.group}>
      <StatusQuoteManager
        id={id}
        contextType='thread'
        rootId={rootId}
        shouldHighlightOnMount={newlyAddedIds.includes(id)}
      />
      {shown.length > 0 && (
        <div ref={repliesRef} className={styles.replies}>
          <div className={styles.repliesInner}>
            {shown.map((replyId, index) => (
              <div className={styles.child} key={replyId}>
                <StatusQuoteManager
                  id={replyId}
                  contextType='thread'
                  previousId={index ? shown[index - 1] : id}
                  nextId={shown[index + 1]}
                  rootId={rootId}
                  shouldHighlightOnMount={newlyAddedIds.includes(replyId)}
                />
              </div>
            ))}
            {visibleCount > 0 && remaining > 0 && (
              <button type='button' className={styles.toggle} onClick={showMore}>
                <FormattedMessage id='local.thread.more_replies' defaultMessage='View {count} more replies' values={{ count: Math.min(10, remaining) }} />
              </button>
            )}
          </div>
        </div>
      )}
      {replies.length > 3 && (
        <button ref={toggleRef} type='button' className={styles.toggle} onClick={visibleCount > 0 ? collapse : showFirst} aria-expanded={visibleCount > 0}>
          {visibleCount > 0
            ? <FormattedMessage id='local.thread.hide_replies' defaultMessage='Hide replies' />
            : <FormattedMessage id='local.thread.view_replies' defaultMessage='View {count} replies' values={{ count: replies.length }} />}
        </button>
      )}
    </div>
  );
};

ReplyGroup.propTypes = {
  id: PropTypes.string.isRequired,
  replies: PropTypes.arrayOf(PropTypes.string).isRequired,
  rootId: PropTypes.string.isRequired,
  newlyAddedIds: PropTypes.arrayOf(PropTypes.string).isRequired,
};

const ThreadedReplies = ({ ids, rootId, newlyAddedIds }) => {
  const statuses = useSelector(state => state.statuses);
  const [visibleGroups, setVisibleGroups] = useState(20);
  const loadMoreRef = useRef(null);
  const loadTriggeredRef = useRef(false);
  const idSet = new Set(ids);
  const children = new Map([[rootId, []]]);

  for (const id of ids) {
    const parentId = statuses.getIn([id, 'in_reply_to_id']);
    const groupId = parentId !== id && idSet.has(parentId) ? parentId : rootId;
    if (!children.has(groupId)) children.set(groupId, []);
    children.get(groupId).push(id);
  }

  const seen = new Set();
  const flatten = id => {
    const result = [];
    for (const childId of children.get(id) || []) {
      if (seen.has(childId)) continue;
      seen.add(childId);
      result.push(childId, ...flatten(childId));
    }
    return result;
  };

  const groups = [];
  for (const id of [...children.get(rootId), ...ids]) {
    if (seen.has(id)) continue;
    seen.add(id);
    groups.push({ id, replies: flatten(id) });
  }

  const showMoreGroups = useCallback(() => setVisibleGroups(count => Math.min(count + 20, groups.length)), [groups.length]);
  const loadMoreByClick = useCallback(() => {
    loadTriggeredRef.current = true;
    showMoreGroups();
  }, [showMoreGroups]);

  useEffect(() => {
    const target = loadMoreRef.current;
    if (!target || typeof IntersectionObserver === 'undefined') return undefined;
    const observer = new IntersectionObserver(entries => {
      if (!entries[0].isIntersecting) {
        loadTriggeredRef.current = false;
      } else if (!loadTriggeredRef.current) {
        loadTriggeredRef.current = true;
        showMoreGroups();
      }
    });
    observer.observe(target);
    return () => observer.disconnect();
  }, [visibleGroups, groups.length, showMoreGroups]);

  return (
    <div>
      {groups.slice(0, visibleGroups).map(({ id, replies }) => (
        <ReplyGroup key={id} id={id} replies={replies} rootId={rootId} newlyAddedIds={newlyAddedIds} />
      ))}
      {visibleGroups < groups.length && (
        <button ref={loadMoreRef} type='button' className={styles.loadMore} onClick={loadMoreByClick}>
          <FormattedMessage id='local.thread.more_comments' defaultMessage='View more comments' />
        </button>
      )}
    </div>
  );
};

ThreadedReplies.propTypes = {
  ids: PropTypes.arrayOf(PropTypes.string).isRequired,
  rootId: PropTypes.string.isRequired,
  newlyAddedIds: PropTypes.arrayOf(PropTypes.string).isRequired,
};

export default ThreadedReplies;
