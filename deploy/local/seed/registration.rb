# Temporary, authenticated exemption for this local registration fixture run only.
Rack::Attack.safelist('local-fixture-registration') do |request|
  expected = ENV.fetch('LOCAL_FIXTURE_KEY', '')
  supplied = request.get_header('HTTP_X_LOCAL_FIXTURE_KEY').to_s
  expected.present? && request.post? && request.path == '/api/v1/accounts' &&
    ActiveSupport::SecurityUtils.secure_compare(expected, supplied)
end
