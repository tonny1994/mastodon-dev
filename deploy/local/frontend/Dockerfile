ARG MASTODON_IMAGE=ghcr.io/mastodon/mastodon:v4.7.2
FROM ${MASTODON_IMAGE} AS release

FROM node:24-bookworm-slim AS frontend
WORKDIR /opt/mastodon
COPY --from=release /opt/mastodon/package.json /opt/mastodon/yarn.lock /opt/mastodon/.yarnrc.yml ./
COPY --from=release /opt/mastodon/streaming/package.json ./streaming/package.json
RUN corepack enable && yarn install --immutable
COPY --from=release /opt/mastodon/app/javascript ./app/javascript
COPY --from=release /opt/mastodon/config ./config
COPY --from=release /opt/mastodon/public ./public
COPY --from=release /opt/mastodon/vite.config.mts /opt/mastodon/tsconfig.json /opt/mastodon/jsconfig.json /opt/mastodon/eslint.config.mjs ./
COPY --from=release /opt/mastodon/.browserslistrc ./
COPY deploy/local/frontend/live.jsx ./app/javascript/mastodon/features/explore/live.jsx
COPY deploy/local/frontend/threaded_replies.jsx deploy/local/frontend/threaded_replies.module.scss ./app/javascript/mastodon/features/status/
COPY deploy/local/frontend/patch-explore.mjs ./patch-explore.mjs
RUN node patch-explore.mjs && \
    yarn exec eslint --ext .jsx --max-warnings 0 app/javascript/mastodon/features/explore/index.tsx app/javascript/mastodon/features/explore/live.jsx app/javascript/mastodon/features/navigation_panel/index.tsx app/javascript/mastodon/features/navigation_panel/components/trends.tsx app/javascript/mastodon/components/status/action_bar.tsx app/javascript/mastodon/features/status/threaded_replies.jsx app/javascript/mastodon/reducers/compose.js && \
    yarn exec eslint --ext .jsx --max-warnings 0 --rule 'react/jsx-no-bind: off' --rule 'react/prop-types: off' app/javascript/mastodon/components/status_action_bar/index.jsx app/javascript/mastodon/features/status/components/action_bar.jsx app/javascript/mastodon/features/status/index.jsx
RUN NODE_OPTIONS=--max-old-space-size=6144 yarn build:production

FROM release
COPY --from=frontend --chown=mastodon:mastodon /opt/mastodon/public/packs ./public/packs
COPY --from=frontend --chown=mastodon:mastodon /opt/mastodon/app/javascript/mastodon/features/explore ./app/javascript/mastodon/features/explore
COPY --from=frontend --chown=mastodon:mastodon /opt/mastodon/app/javascript/mastodon/features/ui/index.jsx ./app/javascript/mastodon/features/ui/index.jsx
COPY --from=frontend --chown=mastodon:mastodon /opt/mastodon/app/javascript/mastodon/features/navigation_panel/index.tsx ./app/javascript/mastodon/features/navigation_panel/index.tsx
COPY --from=frontend --chown=mastodon:mastodon /opt/mastodon/app/javascript/mastodon/features/navigation_panel/components/trends.tsx ./app/javascript/mastodon/features/navigation_panel/components/trends.tsx
COPY --from=frontend --chown=mastodon:mastodon /opt/mastodon/app/javascript/mastodon/components/status_action_bar/index.jsx ./app/javascript/mastodon/components/status_action_bar/index.jsx
COPY --from=frontend --chown=mastodon:mastodon /opt/mastodon/app/javascript/mastodon/components/status/action_bar.tsx ./app/javascript/mastodon/components/status/action_bar.tsx
COPY --from=frontend --chown=mastodon:mastodon /opt/mastodon/app/javascript/mastodon/features/status/components/action_bar.jsx ./app/javascript/mastodon/features/status/components/action_bar.jsx
COPY --from=frontend --chown=mastodon:mastodon /opt/mastodon/app/javascript/mastodon/features/status/index.jsx ./app/javascript/mastodon/features/status/index.jsx
COPY --from=frontend --chown=mastodon:mastodon /opt/mastodon/app/javascript/mastodon/reducers/compose.js ./app/javascript/mastodon/reducers/compose.js
COPY --from=frontend --chown=mastodon:mastodon /opt/mastodon/app/javascript/mastodon/features/status/threaded_replies.jsx /opt/mastodon/app/javascript/mastodon/features/status/threaded_replies.module.scss ./app/javascript/mastodon/features/status/
COPY --from=frontend --chown=mastodon:mastodon /opt/mastodon/app/javascript/mastodon/locales/en.json /opt/mastodon/app/javascript/mastodon/locales/zh-CN.json ./app/javascript/mastodon/locales/
