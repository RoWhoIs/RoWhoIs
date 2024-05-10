package proxypool

import (
	"log"
	"net/http"
	"net/url"
	"sync"
)

type ProxyPool struct {
	proxies           []Proxy
	endpointNextProxy map[string]int
	endPointLock      *sync.Mutex
}

type Proxy struct {
	Client *http.Client
	Config ProxyConfig
}

type ProxyConfig struct {
	Host     string
	Password string
	Username string
}

func NewProxyPool(proxyConfigs []ProxyConfig) *ProxyPool {
	pool := &ProxyPool{
		proxies:           make([]Proxy, 0),
		endPointLock:      &sync.Mutex{},
		endpointNextProxy: make(map[string]int),
	}
	for _, config := range proxyConfigs {
		pool.proxies = append(pool.proxies, Proxy{
			Client: &http.Client{Transport: &http.Transport{Proxy: http.ProxyURL(&url.URL{
				Scheme: "http",
				User:   url.UserPassword(config.Username, config.Password),
				Host:   config.Host,
			})}},
			Config: config,
		})
	}
	return pool
}

func (p *ProxyPool) Do(request *http.Request) (*Proxy, error) {
}

func (p *ProxyPool) GetProxy(endpoint string) (*Proxy, error) {
	p.endPointLock.Lock()
	defer p.endPointLock.Unlock()

	nextProxy := p.endpointNextProxy[endpoint]
	proxy := &p.proxies[nextProxy]
	p.endpointNextProxy[endpoint] = (nextProxy + 1) % len(p.proxies)
	log.Println(proxy.Config)
	return proxy, nil
}
