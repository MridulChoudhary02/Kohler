/** @type {import('next').NextConfig} */
const isDev = process.env.NODE_ENV === 'development' || process.env.npm_lifecycle_event === 'dev';

const nextConfig = {
  reactStrictMode: true,
  distDir: isDev ? '.next-dev' : '.next',
};

export default nextConfig;
