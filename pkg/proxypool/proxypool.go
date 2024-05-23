package proxypool

import (
	"encoding/base64"
	"fmt"
	"log"
	"net/http"
	"net/url"
	"sync"
)

type ProxyPool struct {
	proxies        []Proxy
	nextProxyForID map[string]int
	lock           *sync.Mutex
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
		proxies:        make([]Proxy, 0),
		lock:           &sync.Mutex{},
		nextProxyForID: make(map[string]int),
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

// getProxy gets the least-recently used proxy associated with a given string.
// This allows distribution across proxies on on a per-endpoint basis, for
// example.
func (p *ProxyPool) getProxy(id string) (*Proxy, error) {
	p.lock.Lock()
	defer p.lock.Unlock()

	nextProxy := p.nextProxyForID[id]
	proxy := &p.proxies[nextProxy]
	p.nextProxyForID[id] = (nextProxy + 1) % len(p.proxies)
	log.Println(proxy.Config)
	return proxy, nil
}

func (p *ProxyPool) Do(request *http.Request) (*http.Response, error) {
	// Get next proxy
	path, err := getPath(request.URL)
	if err != nil {
		return nil, fmt.Errorf("getting endpoint")
	}
	proxy, err := p.getProxy(path)
	if err != nil {
		return nil, fmt.Errorf("getting proxy: %v", err)
	}

	// Add proxy auth headers
	auth := fmt.Sprintf("%s:%s", proxy.Config.Username, proxy.Config.Password)
	basicAuth := "Basic " + base64.StdEncoding.EncodeToString([]byte(auth))
	request.Header.Add("Proxy-Authorization", basicAuth)

	// Make request
	resp, err := proxy.Client.Do(request)
	if err != nil {
		return nil, fmt.Errorf("making request: %v", err)
	}
	return resp, nil
}

func getPath(url *url.URL) (string, error) {
	// Need to check scheme or else url.Path returns weird results, e.g.
	// example.com/foobar would return itself, instead of just '/foobar'.
	if url.Scheme == "" {
		return "", fmt.Errorf("no scheme provided")
	}
	return url.Path, nil
}
