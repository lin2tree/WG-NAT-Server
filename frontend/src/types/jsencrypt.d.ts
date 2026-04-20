declare module 'jsencrypt' {
  export default class JSEncrypt {
    constructor(options?: { default_key_size?: string })
    setPublicKey(key: string): void
    setPrivateKey(key: string): void
    encrypt(data: string): string | false
    encryptOAEP(data: string): string | false
    decrypt(data: string): string | false
    getPublicKey(): string
    getPrivateKey(): string
    getPublicKeyB64(): string
    getPrivateKeyB64(): string
  }
}
