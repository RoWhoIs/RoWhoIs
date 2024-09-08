package server

import (
	"net/http"
)

//func testProxies(proxies *[]string, username *string, password *string) *[]string {
//	for _, proxy := range *proxies {
//{		url := "http://" + proxy
//		client := &http.Client{
//}			Transport: &http.Transport{
//				Proxy: http.ProxyURL(&url.URL{
//					Scheme: "http",
//					Host:   proxy,
//				}),
//			},
//		}
//		resp, err := client.Get("https://api.roblox.com/users/1")
//		if err != nil {
//			continue
//		}
//		if resp.StatusCode != 200 {
//			// Remove proxy from list
//			*proxies = append((*proxies)[:0], (*proxies)[1:]...)
//		}
//	}
//	return proxies
//}

func Roquest(method string, node string, path string, args *[]string, respChan chan<- http.Response, errChan chan<- error) {
	client := &http.Client{}

	switch method {
	case "get":
		resp, err := client.Get(node + path)
		respChan <- *resp
		errChan <- err
	case "post":
		resp, err := client.Post(node+path, "application/json", nil)
		respChan <- *resp
		errChan <- err
	}
}
