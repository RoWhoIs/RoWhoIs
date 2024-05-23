package proxypool

import (
	"net/url"
	"testing"
)

func Test_getEndpoint(t *testing.T) {
	for i, tc := range []struct {
		want string
		test string
		err  bool
	}{
		{err: false, test: "https://www.roblox.com/v1/users/avatar-headshot", want: "/v1/users/avatar-headshot"},
		{err: false, test: "http://www.roblox.com/v1/users/avatar-headshot", want: "/v1/users/avatar-headshot"},
		{err: false, test: "https://thumbnails.roblox.com/v1/users/avatar-headshot?userids", want: "/v1/users/avatar-headshot"},
		{err: false, test: "https://thumbnails.roblox.com/v1/users/avatar-headshot?userid=1234#asdf", want: "/v1/users/avatar-headshot"},
		{err: true, test: "thumbnails.roblox.com/v1/users/avatar-headshot?userid=1234#asdf"},
		{err: true, test: "roblox.com/v1/users/avatar-headshot?userid=1234#asdf"},
		{err: true, test: "/v1/users/avatar-headshot?userid=1234#asdf"},
	} {
		testURL, err := url.Parse(tc.test)
		if err != nil {
			t.Errorf("parsing: %v", err)
		}
		got, err := getPath(testURL)
		if err != nil && tc.err {
			continue
		}
		if err != nil {
			t.Errorf("expected no error, got: %v", err)
		}
		if err == nil && tc.err {
			t.Errorf("expected err, but was nil")
		}
		if tc.want != got {
			t.Errorf("case %d: want %s, got: %s", i, tc.want, got)
		}
	}

}
