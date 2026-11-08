import base from './eslint.config.mjs';

export default [
  ...base,
  {
    files: ['src/js/**/*.js'],
    rules: {
      'no-eval': 'error',
      'no-implied-eval': 'error',
      'no-new-func': 'error',
      'no-script-url': 'error',
    },
  },
];
