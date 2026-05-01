/**
 * Hardcoded sample Adaptive Card response — used in dev mode so the UI can
 * be previewed without the FastAPI backend running.
 *
 * Shape matches the real /api/chat ChatResponse + question/timestamp added
 * by App when an output is rendered.
 */

export const SAMPLE_CARD = {
  type: 'AdaptiveCard',
  $schema: 'http://adaptivecards.io/schemas/adaptive-card.json',
  version: '1.5',
  body: [
    {
      type: 'TextBlock',
      text: '📊 RX Commercial Intelligence',
      weight: 'Bolder',
      size: 'Medium',
      color: 'Accent',
    },
    {
      type: 'TextBlock',
      text: 'Top 5 routes by revenue in the last 30 days',
      wrap: true,
      isSubtle: true,
      size: 'Small',
    },
    { type: 'TextBlock', text: '---', spacing: 'Small' },
    {
      type: 'TextBlock',
      text: 'RUH–DXB led revenue at SAR 18.4M, with RUH–LHR close behind at SAR 16.9M. The top 5 contributed 62% of total system revenue.',
      wrap: true,
      weight: 'Bolder',
    },
    {
      type: 'TextBlock',
      text: '📈 Key Findings',
      weight: 'Bolder',
      spacing: 'Medium',
    },
    {
      type: 'TextBlock',
      text: '• RUH–DXB: SAR 18.4M (load factor 88%, yield SAR 0.42/RPK)',
      wrap: true,
      spacing: 'None',
    },
    {
      type: 'TextBlock',
      text: '• RUH–LHR: SAR 16.9M (load factor 81%, yield SAR 0.55/RPK)',
      wrap: true,
      spacing: 'None',
    },
    {
      type: 'TextBlock',
      text: '• RUH–CAI: SAR 11.2M (load factor 84%)',
      wrap: true,
      spacing: 'None',
    },
    {
      type: 'TextBlock',
      text: '• RUH–IST: SAR 9.8M (load factor 79%)',
      wrap: true,
      spacing: 'None',
    },
    {
      type: 'TextBlock',
      text: '• RUH–JFK: SAR 8.6M (load factor 73%, premium mix 31%)',
      wrap: true,
      spacing: 'None',
    },
    {
      type: 'TextBlock',
      text: '⚠️ Flags',
      weight: 'Bolder',
      spacing: 'Medium',
      color: 'Warning',
    },
    {
      type: 'TextBlock',
      text: '• RUH–JFK load factor below 75% target — investigate seasonality',
      wrap: true,
      spacing: 'None',
      color: 'Warning',
    },
    {
      type: 'TextBlock',
      text: '💡 Recommendation',
      weight: 'Bolder',
      spacing: 'Medium',
    },
    {
      type: 'TextBlock',
      text: 'Consider a targeted fare promotion on RUH–JFK economy and review premium upsell on RUH–LHR where yield is strongest.',
      wrap: true,
    },
    {
      type: 'ActionSet',
      actions: [
        {
          type: 'Action.ToggleVisibility',
          title: 'Show DAX Query',
          targetElements: ['daxBlock'],
        },
      ],
    },
    {
      type: 'TextBlock',
      id: 'daxBlock',
      text: '```\nEVALUATE\nTOPN(\n  5,\n  SUMMARIZECOLUMNS(\n    Routes[OriginDestination],\n    "Revenue", [Total Revenue]\n  ),\n  [Revenue], DESC\n)\n```',
      wrap: true,
      fontType: 'Monospace',
      size: 'Small',
      isVisible: false,
    },
  ],
};

export const SAMPLE_DAX = `EVALUATE
TOPN(
  5,
  SUMMARIZECOLUMNS(
    Routes[OriginDestination],
    "Revenue", [Total Revenue]
  ),
  [Revenue], DESC
)`;

export const SAMPLE_SUMMARY =
  'RUH–DXB led revenue at SAR 18.4M, with RUH–LHR close behind at SAR 16.9M. The top 5 contributed 62% of total system revenue.';

export const SAMPLE_QUESTION = 'Top 5 routes by revenue in the last 30 days';
