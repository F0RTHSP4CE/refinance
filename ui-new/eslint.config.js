import js from '@eslint/js'
import globals from 'globals'
import importPlugin from 'eslint-plugin-import'
import reactPlugin from 'eslint-plugin-react'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist', 'node_modules', '*.config.*', 'vite.config.ts']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    plugins: {
      react: reactPlugin,
      import: importPlugin,
    },
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    settings: {
      react: {
        version: 'detect',
      },
    },
    rules: {
      'react/display-name': 'off',
      'react/react-in-jsx-scope': 'off',
      'react/jsx-no-useless-fragment': ['error', { allowExpressions: true }],
      'import/no-default-export': 'error',
      '@typescript-eslint/no-unused-vars': [
        'error',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
          caughtErrorsIgnorePattern: '^_',
        },
      ],
      'no-restricted-syntax': [
        'error',
        {
          selector:
            "AssignmentExpression[left.type='MemberExpression'][left.property.name='displayName']",
          message:
            'Do not use component.displayName; prefer named function components.',
        },
        {
          selector:
            "ClassDeclaration[superClass.object.name='React'][superClass.property.name='Component']",
          message:
            'Class components are not allowed. Use function components and hooks.',
        },
        {
          selector:
            "ClassDeclaration[superClass.object.name='React'][superClass.property.name='PureComponent']",
          message:
            'Class components are not allowed. Use function components and hooks.',
        },
        {
          selector: "ClassDeclaration[superClass.name='Component']",
          message:
            'Class components are not allowed. Use function components and hooks.',
        },
        {
          selector: "ClassDeclaration[superClass.name='PureComponent']",
          message:
            'Class components are not allowed. Use function components and hooks.',
        },
      ],
    },
  },
])
