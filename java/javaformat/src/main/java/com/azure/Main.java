// Copyright (c) Microsoft Corporation. All rights reserved.
// Licensed under the MIT License.

package com.azure;

import com.google.googlejavaformat.java.Formatter;

public class Main {

    public static void main(String[] args) throws Exception {
        String code = System.getenv("JAVA_CODE");

        Formatter formatter = new Formatter();
        String formattedCode = formatter.formatSourceAndFixImports(code);

        // run with "mvn --quiet package exec:java"
        System.out.println(formattedCode);
    }
}
