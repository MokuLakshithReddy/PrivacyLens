declare module 'psl' {
  export function parse(hostname: string): {
    domain: string | null;
    subdomain: string | null;
    listed: boolean;
    input: string;
    tld: string | null;
  };
}
