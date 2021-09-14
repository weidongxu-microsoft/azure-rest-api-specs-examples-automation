// Copyright (c) Microsoft Corporation. All rights reserved.
// Licensed under the MIT License.

package com.azure;

import com.google.googlejavaformat.java.Formatter;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

public class Main {

    public static void main(String[] args) throws Exception {
        assert(args.length > 0);

        String filepath = args[0];
        String code = Files.readString(Path.of(filepath), StandardCharsets.UTF_8);

        Formatter formatter = new Formatter();
        String formattedCode = formatter.formatSourceAndFixImports(code);

        // run with "mvn --quiet package exec:java"
        System.out.println(formattedCode);
    }
}
