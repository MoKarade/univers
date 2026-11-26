export default [
  {
    files: ['app/src/*.js'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'script',
    },
    rules: {
      'no-dupe-keys': 'error',
      'no-dupe-args': 'error',
      'no-duplicate-case': 'error',
      'no-unreachable': 'error',
      'no-constant-condition': ['warn', { checkLoops: false }],
      'use-isnan': 'error',
      'valid-typeof': 'error',
    },
  },
];
