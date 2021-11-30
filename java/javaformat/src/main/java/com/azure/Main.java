// Copyright (c) Microsoft Corporation. All rights reserved.
// Licensed under the MIT License.

package com.azure;

import com.google.googlejavaformat.java.Formatter;

import java.nio.charset.StandardCharsets;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.Path;

public class Main {

    // run with "mvn --quiet package exec:java"

    public static void main(String[] args) throws Exception {
        assert args.length > 0;

        String srcPath = args[0];
        Path srcDir = Path.of(srcPath);

        assert Files.isDirectory(srcDir);

        Formatter formatter = new Formatter();
        DirectoryStream<Path> directoryStream =
                Files.newDirectoryStream(srcDir, entry -> entry.toString().endsWith(".java"));
        for (Path path : directoryStream) {
            if (Files.isRegularFile(path)) {
                String code = Files.readString(path, StandardCharsets.UTF_8);
                String formattedCode = formatter.formatSourceAndFixImports(code);
                Files.write(path, formattedCode.getBytes(StandardCharsets.UTF_8));
            }
        }
    }
}
